// /version.json (#372): the version and the commit built (macros.py version), and when.
import { version } from '../macros.json';

export const GET = () => Response.json({ ...version, built_at: new Date().toISOString() });
