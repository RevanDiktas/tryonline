'use client';

import Link from 'next/link';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link href="/" className="text-xl font-bold tracking-tight text-black">TRYON</Link>
          <Link href="/" className="text-sm text-gray-500 hover:text-black transition">Back to Home</Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-black mb-2">Privacy Policy</h1>
        <p className="text-gray-500 text-sm mb-10">Last updated: February 27, 2026</p>

        <div className="prose prose-gray max-w-none space-y-8 text-gray-700 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-black mt-0">1. Introduction</h2>
            <p>
              TRYON (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) operates the TRYON virtual try-on platform, including the website at tryonline.vercel.app and the TRYON Shopify app. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">2. Information We Collect</h2>
            <h3 className="text-base font-medium text-black mt-4">Account Information</h3>
            <p>When you create an account, we collect your name, email address, phone number, and country. For brand accounts, we also collect your brand name and Shopify store domain.</p>

            <h3 className="text-base font-medium text-black mt-4">Body Measurements &amp; Photos</h3>
            <p>Shoppers who use the virtual try-on feature provide body measurements (height, weight, chest, waist, hips, etc.) and a full-body photo. This data is used to generate a 3D avatar for the try-on experience. Photos are processed and stored securely.</p>

            <h3 className="text-base font-medium text-black mt-4">Usage Data</h3>
            <p>We collect analytics about how you interact with the try-on widget, including which sizes you view, size recommendations, and add-to-cart events. This data helps brands understand fit and reduce returns.</p>

            <h3 className="text-base font-medium text-black mt-4">Authentication Data</h3>
            <p>If you sign in with Google or Apple, we receive your name and email address from the provider. We do not receive or store your password from these services.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">3. How We Use Your Information</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>To provide and maintain the virtual try-on service</li>
              <li>To generate your 3D avatar and size recommendations</li>
              <li>To provide brands with anonymized analytics about fit and sizing</li>
              <li>To communicate with you about your account and updates</li>
              <li>To improve our service and develop new features</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">4. Data Sharing</h2>
            <p>We do not sell your personal information. We share data only in the following cases:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>With brands:</strong> Anonymized and aggregated analytics (size distribution, conversion rates). Brands cannot see individual shopper identities or photos.</li>
              <li><strong>Service providers:</strong> We use Supabase for database and authentication, Vercel for hosting, and Railway for our API. These providers process data on our behalf.</li>
              <li><strong>Legal requirements:</strong> When required by law or to protect our rights.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">5. Data Storage &amp; Security</h2>
            <p>Your data is stored securely using Supabase (hosted on AWS) with row-level security policies. Photos and 3D models are stored in encrypted storage buckets. We use HTTPS for all data transmission.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">6. Your Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Access</strong> your personal data</li>
              <li><strong>Correct</strong> inaccurate data</li>
              <li><strong>Delete</strong> your account and all associated data</li>
              <li><strong>Export</strong> your data in a portable format</li>
              <li><strong>Withdraw consent</strong> for data processing at any time</li>
            </ul>
            <p className="mt-3">To exercise any of these rights, contact us at privacy@tryonline.app.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">7. Data Retention</h2>
            <p>We retain your data for as long as your account is active. When you delete your account, we remove all personal data including photos, measurements, and avatars within 30 days. Anonymized analytics data may be retained.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">8. Shopify Store Data</h2>
            <p>When brands install the TRYON Shopify app, we access only the data necessary to provide our service (product information, shop domain). We comply with Shopify&apos;s API Terms of Service and mandatory GDPR webhooks for data deletion requests.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">9. Cookies &amp; Local Storage</h2>
            <p>We use localStorage (not cookies) to maintain your session. We do not use third-party tracking cookies. The try-on widget uses localStorage for session persistence, which works within Shopify store iframes.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">10. Changes to This Policy</h2>
            <p>We may update this policy from time to time. We will notify you of any material changes by posting the new policy on this page and updating the &quot;Last updated&quot; date.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-black">11. Contact Us</h2>
            <p>If you have questions about this Privacy Policy, contact us at:</p>
            <p className="mt-2">
              <strong>Email:</strong> privacy@tryonline.app<br />
              <strong>Website:</strong> tryonline.vercel.app
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
