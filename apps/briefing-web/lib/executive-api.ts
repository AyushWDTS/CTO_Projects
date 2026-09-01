import { createApiClient, type QueryParams } from "@wdts/api-client";

/** Browser calls same-origin BFF only — never the gateway or API key. */
export const executiveApi = createApiClient({ baseUrl: "/executive/api" });

export type { QueryParams };
