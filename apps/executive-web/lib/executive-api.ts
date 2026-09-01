import { createApiClient } from "@wdts/api-client";

/** Browser calls same-origin BFF only — never the MCP host or API key. */
export const executiveApi = createApiClient({ baseUrl: "/executive/api" });
