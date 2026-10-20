import { metadataOptions, resourceMetadata } from '@/lib/mcp/resource-metadata';

export const dynamic = 'force-dynamic';
export const GET = (req: Request) => resourceMetadata(req);
export const OPTIONS = () => metadataOptions();
