/**
 * TryOn MCP server: https://tryon.global/mcp (Streamable HTTP; mcp-handler serves the
 * 2026-07-28 spec and falls back for 2025-era clients).
 *
 * For shoppers using an AI assistant (Claude, ChatGPT, ...) to shop: link a TryOn account once
 * (OAuth on Supabase Auth, consent on /oauth/consent), then ask "what size should I get?" for
 * any Shopify product link. Sizes come from the same engine and the same calls as the Find my
 * size card (lib/mcp/sizing.ts), from the shopper's fit passport or their size quiz answers.
 *
 * Tools (annotations matter: both directories reject tools without them):
 *   get_my_fit_passport   read    what TryOn knows about the shopper's body
 *   save_my_size_profile  write   the seven quiz answers, given in the chat
 *   recommend_size        read    the size for a product link, with the in-chat size card
 *   save_to_wishlist      write   add the product to the TryOn wishlist
 */
import { createMcpHandler, withMcpAuth } from 'mcp-handler';
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps/server';
import { z } from 'zod';
import { verifyAccessToken } from '@/lib/mcp/auth';
import { fetchShopifyProduct, ProductUrlError, type ShopifyProduct } from '@/lib/mcp/product';
import { garmentFromProduct, sizeFor, type Fit, type QuizAnswers, type SizeAnswer } from '@/lib/mcp/sizing';
import { addToWishlist, bodyFor, getBrandGarment, getPassport, getQuizAnswers, saveQuizAnswers } from '@/lib/mcp/tryon-api';
import { EXT_APPS_URL, SIZE_CARD_HTML, SIZE_CARD_URI } from '@/lib/mcp/size-card';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// withMcpAuth builds resource_metadata as <origin> + METADATA_PATH, so this is the ORIGIN
// (the resource itself, https://tryon.global/mcp, is named in lib/mcp/resource-metadata.ts).
const PUBLIC_ORIGIN = 'https://tryon.global';
const METADATA_PATH = '/.well-known/oauth-protected-resource/mcp';
const MEASURE_URL = 'https://tryon.global/onboarding';

type Ctx = { http?: { authInfo?: { token: string; extra?: Record<string, unknown> } } };

function who(ctx: Ctx): { userId: string; token: string } {
  const a = ctx.http?.authInfo;
  const userId = a?.extra?.userId;
  if (!a?.token || typeof userId !== 'string') throw new Error('Not signed in to TryOn. Reconnect the TryOn app.');
  return { userId, token: a.token };
}

const text = (t: string) => ({ content: [{ type: 'text' as const, text: t }] });
const fail = (t: string) => ({ ...text(t), isError: true });
const up = (s: string) => s.toUpperCase();

const fitSchema = z.enum(['slim', 'regular', 'loose']).optional()
  .describe('How the shopper likes clothes to fit. Leave out to use their saved preference (regular by default).');

export interface SizeCardData {
  product: Pick<ShopifyProduct, 'url' | 'host' | 'title' | 'image' | 'price' | 'currency' | 'storeName' | 'sizes'>;
  answer: SizeAnswer;
  brandChart: boolean;
}

function describeAnswer(p: ShopifyProduct, a: SizeAnswer, brandChart: boolean): string {
  const lines = [
    `${a.basis === 'measured' ? 'Size' : 'Estimated size'} for ${p.title}${p.storeName ? ` (${p.storeName})` : ''}: ${up(a.size)}, ${a.match}% match.`,
    a.reasoning,
  ];
  if (a.soldOut) lines.push(a.nextInStock ? `${up(a.size)} is sold out; the best size in stock is ${up(a.nextInStock)} (${Math.round(a.scores[a.nextInStock] || 0)}% match).` : `${up(a.size)} is sold out, and none of the sizes in stock is likely to fit this shopper. Do not suggest buying another size; suggest checking back or a similar product.`);
  else if (a.between) lines.push(`Between ${up(a.size)} and ${up(a.between)}.`);
  lines.push(`All sizes: ${p.sizes.map((s) => `${up(s.label)} ${Math.round(a.scores[s.label] || 0)}%${s.available ? '' : ' (sold out)'}`).join(', ')}.`);
  lines.push(a.basis === 'measured'
    ? 'Based on the shopper\'s measured TryOn fit passport.'
    : `Estimated from the shopper's answers (height, weight, age, build), not a measurement. A photo fit passport at ${MEASURE_URL} makes it exact.`);
  if (brandChart) lines.push('This store uses TryOn, so its own size chart was used.');
  return lines.join('\n');
}

const handler = createMcpHandler(
  (server) => {
    server.registerTool(
      'get_my_fit_passport',
      {
        title: 'Get my fit passport',
        description: 'What TryOn knows about the signed-in shopper\'s body: their measured fit passport (chest, waist, hips and more, in cm) or, if they have not measured, their size quiz answers. Use before talking about the shopper\'s size in general. Returns nothing personal beyond body sizes.',
        inputSchema: z.object({}),
        annotations: { title: 'Get my fit passport', readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      },
      async (_args: Record<string, never>, ctx: Ctx) => {
        const { userId, token } = who(ctx);
        const passport = await getPassport(userId, token);
        if (passport.measured) {
          const m = passport.measured.measurements;
          const parts = Object.entries(m).map(([k, v]) => `${k.replace('_', ' ')} ${Math.round(v)} cm`);
          return { ...text(`Measured fit passport${passport.measuredAt ? ` (measured ${passport.measuredAt.slice(0, 10)})` : ''}: ${parts.join(', ')}. Preferred fit: ${passport.measured.fit || 'regular'}.`), structuredContent: { basis: 'measured', measurements: m, fit: passport.measured.fit || 'regular' } };
        }
        const answers = await getQuizAnswers(userId, token);
        if (answers) {
          return { ...text(`No measured fit passport yet${passport.status === 'processing' ? ' (one is being built right now)' : ''}. Size quiz answers on file: ${answers.gender}, ${answers.height} cm, ${answers.weight} kg${answers.age ? `, age ${answers.age}` : ''}, fit ${answers.fit || 'regular'}. Sizes from these are estimates. A photo fit passport at ${MEASURE_URL} measures the shopper exactly.`), structuredContent: { basis: 'estimate', answers } };
        }
        return { ...text(`This shopper has no fit passport and no size quiz answers yet. Ask them: are they shopping women's or men's sizes, their height and weight, their age, and their build (${'women: bust smaller/average/fuller and hips narrower/average/wider; men: chest and shoulders slimmer/average/broader and belly flatter/average/rounder'}), then call save_my_size_profile. Or they can measure from one photo at ${MEASURE_URL}.`), structuredContent: { basis: 'none' } };
      },
    );

    server.registerTool(
      'save_my_size_profile',
      {
        title: 'Save my size answers',
        description: 'Save the shopper\'s size quiz answers to their TryOn account (replaces earlier answers), so every store and chat can estimate their size. Only call with answers the shopper gave you; never guess them. Not needed if they have a measured fit passport.',
        inputSchema: z.object({
          sizes_for: z.enum(['female', 'male']).describe('Women\'s or men\'s sizes.'),
          height_cm: z.number().min(120).max(230).describe('Height in cm (convert from feet and inches if needed).'),
          weight_kg: z.number().min(30).max(250).describe('Weight in kg (convert from pounds if needed).'),
          age: z.number().int().min(14).max(100).optional(),
          build: z.object({
            chest: z.union([z.literal(-1), z.literal(0), z.literal(1)]).optional().describe('Women: bust smaller -1 / average 0 / fuller 1. Men: chest and shoulders slimmer -1 / average 0 / broader 1.'),
            belly: z.union([z.literal(-1), z.literal(0), z.literal(1)]).optional().describe('Men only: belly flatter -1 / average 0 / rounder 1.'),
            hips: z.union([z.literal(-1), z.literal(0), z.literal(1)]).optional().describe('Women only: hips narrower -1 / average 0 / wider 1.'),
          }).optional(),
          fit: fitSchema,
        }),
        annotations: { title: 'Save my size answers', readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: false },
      },
      async (args: { sizes_for: 'female' | 'male'; height_cm: number; weight_kg: number; age?: number; build?: QuizAnswers['shape']; fit?: Fit }, ctx: Ctx) => {
        const { userId, token } = who(ctx);
        const shape = { ...(args.build || {}) };
        if (args.sizes_for === 'male') delete shape.hips; else delete shape.belly;
        const answers: QuizAnswers = { gender: args.sizes_for, height: Math.round(args.height_cm), weight: Math.round(args.weight_kg), age: args.age, shape, fit: args.fit };
        await saveQuizAnswers(userId, token, answers);
        return text('Saved to the shopper\'s TryOn account. recommend_size will now estimate their size for any product.');
      },
    );

    registerAppTool(
      server,
      'recommend_size',
      {
        title: 'Recommend my size',
        description: 'The shopper\'s size for a clothing product, from a product page link on any Shopify store: the best size with a % match for every size, stock, and a short reason. Uses their measured fit passport, else their size quiz answers. Call whenever the shopper looks at or is about to buy clothes or shoes with sizes.',
        inputSchema: z.object({
          product_url: z.string().url().describe('The product page link, e.g. https://store.com/products/linen-shirt'),
          fit: fitSchema,
          country: z.string().length(2).optional().describe('Shopper\'s country (ISO 3166 alpha-2) if known; sizes run differently by region.'),
        }),
        annotations: { title: 'Recommend my size', readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
        _meta: { ui: { resourceUri: SIZE_CARD_URI } },
      },
      async (args: { product_url: string; fit?: Fit; country?: string }, ctx: Ctx) => {
        const { userId, token } = who(ctx);
        let product: ShopifyProduct | null;
        try { product = await fetchShopifyProduct(args.product_url); } catch (e) {
          return fail(e instanceof ProductUrlError ? e.message : 'Could not read that product page.');
        }
        if (!product) return fail('Could not read sizes from that page. TryOn reads Shopify stores; for other stores, tell the shopper their estimated size from get_my_fit_passport instead.');
        if (!product.sizes.length) return fail(`${product.title} has no sizes to choose from (one size, or not clothing).`);

        const { body } = await bodyFor(userId, token);
        if (!body) {
          return fail(`TryOn has no sizes for this shopper yet. Ask their women's or men's sizes, height, weight, age and build, and call save_my_size_profile; then call recommend_size again. Or they can measure from one photo at ${MEASURE_URL}.`);
        }
        const brand = product.shop ? await getBrandGarment(product.shop, product.handle).catch(() => null) : null;
        const garment = brand || garmentFromProduct(product.productType, product.title);
        const answer = sizeFor(body, product.sizes, garment, args.fit, args.country || product.storeCountry);
        if (!answer) return fail('Could not work out a size for this product.');
        const brandChart = !!brand && Object.keys(brand.chart).length > 0;
        const data: SizeCardData = {
          product: { url: product.url, host: product.host, title: product.title, image: product.image, price: product.price, currency: product.currency, storeName: product.storeName || product.vendor, sizes: product.sizes },
          answer,
          brandChart,
        };
        return { ...text(describeAnswer(product, answer, brandChart)), structuredContent: data as unknown as Record<string, unknown> };
      },
    );

    server.registerTool(
      'save_to_wishlist',
      {
        title: 'Save to my TryOn wishlist',
        description: 'Add a product (by its product page link) to the shopper\'s TryOn wishlist. Saving the same product twice keeps one entry.',
        inputSchema: z.object({ product_url: z.string().url().describe('The product page link.') }),
        annotations: { title: 'Save to my TryOn wishlist', readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      },
      async (args: { product_url: string }, ctx: Ctx) => {
        const { token } = who(ctx);
        let product: ShopifyProduct | null;
        try { product = await fetchShopifyProduct(args.product_url); } catch (e) {
          return fail(e instanceof ProductUrlError ? e.message : 'Could not read that product page.');
        }
        if (!product) return fail('Could not read that product page. TryOn reads Shopify stores.');
        await addToWishlist(token, {
          productId: product.handle, shopDomain: product.shop || product.host, productName: product.title,
          imageUrl: product.image, price: product.price, currency: product.currency, brandName: product.storeName || product.vendor,
        });
        return text(`Saved ${product.title} to the shopper's TryOn wishlist.`);
      },
    );

    registerAppResource(
      server,
      'TryOn size card',
      SIZE_CARD_URI,
      { description: 'The shopper\'s size for a product, with a % match for every size.' },
      async () => ({
        contents: [{
          uri: SIZE_CARD_URI,
          mimeType: RESOURCE_MIME_TYPE,
          text: SIZE_CARD_HTML,
          _meta: {
            ui: {
              csp: {
                // The MCP Apps client (served by us) and product photos (Shopify's CDN; some
                // stores serve them from their own domain, those show without a photo).
                resourceDomains: [new URL(EXT_APPS_URL).origin, 'https://cdn.shopify.com'],
                connectDomains: [],
              },
              prefersBorder: false,
            },
          },
        }],
      }),
    );
  },
  { serverInfo: { name: 'TryOn', version: '1.0.0' } },
);

const authed = withMcpAuth(handler, (_req, token) => verifyAccessToken(token), {
  required: true,
  resourceMetadataPath: METADATA_PATH,
  resourceUrl: PUBLIC_ORIGIN,
});

export { authed as GET, authed as POST, authed as DELETE };
