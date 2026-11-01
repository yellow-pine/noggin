// /version.json (#372): the version and the commit built (macros.py build), and when.
import { build } from '../macros.json';

export const GET = () => Response.json({ ...build, built_at: new Date().toISOString() });
