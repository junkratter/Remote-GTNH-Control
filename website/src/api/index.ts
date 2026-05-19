// Typed API client built on `openapi-fetch` + the generated `schema.d.ts`.
//
// Регенерация типов:
//   npm run openapi:fetch          # стянуть свежую openapi.json с бэка
//   npm run openapi:generate       # пересобрать schema.d.ts из openapi.json
//
// Использование (пример):
//   import { api } from "@/api"
//   const { data, error } = await api.GET("/api/info/version")
//   if (data?.code === 200) { ... }

import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./generated/schema";

import Setting from "@/utils/setting";
import { envelopeList, envelopePayload } from "@/utils/apiEnvelope";

function apiBaseUrl() {
    const configured = (Setting.get("backendUrl") || "").replace(/\/$/, "");
    return configured || (typeof window !== "undefined" ? window.location.origin : "");
}

const tokenMiddleware: Middleware = {
    async onRequest({ request }) {
        const token = Setting.get("token");
        if (token) {
            request.headers.set("X-Server-Token", token);
        }
        return request;
    },
};

const baseUrl = Setting.get("backendUrl") || "/";
export const api = createClient<paths>({ baseUrl });
api.use(tokenMiddleware);

// Удобные шорткаты по модулям. Все обёртки возвращают `data` или бросают.
async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown }>): Promise<T> {
    const { data, error } = await promise;
    if (error || !data) {
        throw new Error(typeof error === "string" ? error : JSON.stringify(error));
    }
    return data;
}

export const taskApi = {
    add: (body: { task_id?: string | null; commands: string[]; client_id?: string | null }) =>
        unwrap(api.POST("/api/task/add", { body })),
};

export const robotsApi = {
    list: async () => envelopeList(await unwrap(api.GET("/api/robots/list", {}))),
    register: async (body: { client_id: string; kind: string; label?: string | null }) =>
        envelopePayload(await unwrap(api.POST("/api/robots/register", { body }))),
    updateState: (
        client_id: string,
        body: { state?: string | null; last_message?: string | null; telemetry?: Record<string, unknown> | null },
    ) =>
        unwrap(
            api.POST("/api/robots/{client_id}/state", {
                params: { path: { client_id } },
                body,
            }),
        ),
    miningJobsList: async () => envelopeList(await unwrap(api.GET("/api/robots/mining-jobs", {}))),
    miningJobCreate: async (body: {
        robot_client_id?: string | null;
        miner_kind?: string;
        dimension?: number;
        x: number;
        y: number;
        z: number;
        note?: string | null;
    }) => envelopePayload(await unwrap(api.POST("/api/robots/mining-jobs", { body }))),
    miningJobNext: async (robot_client_id: string) => {
        const base = apiBaseUrl();
        const url = new URL(`${base}/api/robots/mining-jobs/next`);
        url.searchParams.set("robot_client_id", robot_client_id);
        const res = await fetch(url.toString(), {
            headers: { "X-Server-Token": Setting.get("token") || "" },
        });
        const json = (await res.json()) as { code?: number; message?: string; data?: unknown };
        if (!res.ok || json.code !== 200) {
            throw new Error(json.message || res.statusText);
        }
        return json;
    },
    /** PATCH not yet in generated OpenAPI — use fetch. */
    async miningJobPatch(id: number, body: Record<string, unknown>) {
        const base = apiBaseUrl();
        const res = await fetch(`${base}/api/robots/mining-jobs/${id}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "X-Server-Token": Setting.get("token") || "",
            },
            body: JSON.stringify(body),
        });
        const json = (await res.json()) as { code?: number; message?: string; data?: unknown };
        if (!res.ok || json.code !== 200) {
            throw new Error(json.message || res.statusText);
        }
        return json;
    },
    miningJobEnqueue: async (id: number, deploy = false) => {
        const base = apiBaseUrl();
        const url = new URL(`${base}/api/robots/mining-jobs/${id}/enqueue`);
        url.searchParams.set("deploy", deploy ? "true" : "false");
        const res = await fetch(url.toString(), {
            method: "POST",
            headers: { "X-Server-Token": Setting.get("token") || "" },
        });
        const json = (await res.json()) as { code?: number; message?: string; data?: unknown };
        if (!res.ok || json.code !== 200) {
            throw new Error(json.message || res.statusText);
        }
        return json;
    },
    powerJobsList: async () => envelopeList(await unwrap(api.GET("/api/robots/power-jobs", {}))),
    powerJobCreate: async (body: {
        robot_client_id?: string | null;
        generator_kind?: string;
        fuel_kind?: string;
        capsule_count?: number;
        dimension?: number;
        x: number;
        y: number;
        z: number;
        note?: string | null;
    }) => envelopePayload(await unwrap(api.POST("/api/robots/power-jobs", { body }))),
    powerJobNext: async (robot_client_id: string) => {
        const base = apiBaseUrl();
        const url = new URL(`${base}/api/robots/power-jobs/next`);
        url.searchParams.set("robot_client_id", robot_client_id);
        const res = await fetch(url.toString(), {
            headers: { "X-Server-Token": Setting.get("token") || "" },
        });
        const json = (await res.json()) as { code?: number; message?: string; data?: unknown };
        if (!res.ok || json.code !== 200) {
            throw new Error(json.message || res.statusText);
        }
        return json;
    },
    async powerJobPatch(id: number, body: Record<string, unknown>) {
        const base = apiBaseUrl();
        const res = await fetch(`${base}/api/robots/power-jobs/${id}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "X-Server-Token": Setting.get("token") || "",
            },
            body: JSON.stringify(body),
        });
        const json = (await res.json()) as { code?: number; message?: string; data?: unknown };
        if (!res.ok || json.code !== 200) {
            throw new Error(json.message || res.statusText);
        }
        return json;
    },
};

async function craftEnvelope<T = unknown>(
    path: string,
    init?: RequestInit,
): Promise<{ code?: number; message?: string; data?: T }> {
    const base = apiBaseUrl();
    const res = await fetch(`${base}${path}`, {
        ...init,
        headers: {
            "Content-Type": "application/json",
            "X-Server-Token": Setting.get("token") || "",
            ...(init?.headers as Record<string, string>),
        },
    });
    const json = (await res.json()) as { code?: number; message?: string; data?: T };
    if (!res.ok || json.code !== 200) {
        throw new Error(json.message || res.statusText);
    }
    return json;
}

export const craftApi = {
    createPlan: (body: {
        goal_alias_id: number;
        amount: number;
        client_id?: string | null;
        ae_stock_client_id?: string | null;
    }) =>
        craftEnvelope(`/api/craft/plan`, {
            method: "POST",
            body: JSON.stringify(body),
        }),
    getPlan: (rootJobId: number) => craftEnvelope(`/api/craft/plan/${rootJobId}`),
    health: () => craftEnvelope(`/api/craft/health`),
    resolveAlias: (nesql_item_id: number, damage = 0) =>
        craftEnvelope(`/api/craft/item-alias?nesql_item_id=${nesql_item_id}&damage=${damage}`),
    stock: (client_id: string, aliasesCsv: string) =>
        craftEnvelope(
            `/api/craft/me/stock?client_id=${encodeURIComponent(client_id)}&aliases=${encodeURIComponent(aliasesCsv)}`,
        ),
    choose: (rootJobId: number, body: { job_id: number; recipe_id: number }) =>
        craftEnvelope(`/api/craft/plan/${rootJobId}/choose`, {
            method: "POST",
            body: JSON.stringify(body),
        }),
    start: (rootJobId: number, body: { client_id?: string | null }) =>
        craftEnvelope(`/api/craft/plan/${rootJobId}/start`, {
            method: "POST",
            body: JSON.stringify(body),
        }),
    cancel: (rootJobId: number) =>
        craftEnvelope(`/api/craft/plan/${rootJobId}/cancel`, {
            method: "POST",
            body: "{}",
        }),
    enqueuePatterns: (
        rootJobId: number,
        body: { client_id: string; patterns: Record<string, unknown>[] },
    ) =>
        craftEnvelope(`/api/craft/plan/${rootJobId}/enqueue_patterns`, {
            method: "POST",
            body: JSON.stringify(body),
        }),
};

export const autocraftApi = {
    listPatterns: () => unwrap(api.GET("/api/autocraft/patterns", {})),
    upsertPattern: (body: {
        interface_address: string;
        slot: number;
        kind: "crafting" | "processing";
        inputs: { name: string; damage?: number; amount?: number; label?: string | null }[];
        outputs: { name: string; damage?: number; amount?: number; label?: string | null }[];
        label?: string | null;
    }) => unwrap(api.POST("/api/autocraft/patterns", { body })),
    deletePattern: (id: number) =>
        unwrap(
            api.DELETE("/api/autocraft/patterns/{pattern_id}", {
                params: { path: { pattern_id: id } },
            }),
        ),
    programPattern: (id: number, client_id: string) =>
        unwrap(
            api.POST("/api/autocraft/patterns/{pattern_id}/program", {
                params: { path: { pattern_id: id } },
                body: { client_id },
            }),
        ),
    requests: (state?: string) =>
        unwrap(
            api.GET("/api/autocraft/requests", {
                params: { query: state ? { state } : {} },
            }),
        ),
    request: (body: {
        client_id: string;
        item_name: string;
        item_damage?: number;
        amount?: number;
        cpu_name?: string | null;
        label?: string | null;
    }) => unwrap(api.POST("/api/autocraft/request", { body })),
    cancelRequest: (id: number) =>
        unwrap(
            api.POST("/api/autocraft/requests/{request_id}/cancel", {
                params: { path: { request_id: id } },
            }),
        ),
    scanCpus: (client_id: string, detail = false) =>
        unwrap(
            api.POST("/api/autocraft/cpus/scan", {
                body: { client_id, detail },
            }),
        ),
};

export const mapApi = {
    blocks: (params: Record<string, string | number>) =>
        unwrap(api.GET("/api/map/blocks", { params: { query: params } })),
};

export const nesqlApi = {
    meta: () => unwrap(api.GET("/api/nesql/meta", {})),
    mods: () => unwrap(api.GET("/api/nesql/mods", {})),
    items: (params: {
        q?: string;
        mod_id?: string;
        limit?: number;
        offset?: number;
    } = {}) => unwrap(api.GET("/api/nesql/items", { params: { query: params } })),
    item: (id: number) =>
        unwrap(api.GET("/api/nesql/items/{item_id}", { params: { path: { item_id: id } } })),
    recipes: (params: {
        output_item_id?: number;
        input_item_id?: number;
        recipe_type?: string;
        limit?: number;
        offset?: number;
    } = {}) => unwrap(api.GET("/api/nesql/recipes", { params: { query: params } })),
    recipe: (id: number) =>
        unwrap(
            api.GET("/api/nesql/recipes/{recipe_id}", {
                params: { path: { recipe_id: id } },
            }),
        ),
    quests: (params: {
        q?: string;
        quest_line?: number;
        limit?: number;
        offset?: number;
    } = {}) => unwrap(api.GET("/api/nesql/quests", { params: { query: params } })),
    quest: (id: number) =>
        unwrap(api.GET("/api/nesql/quests/{quest_id}", { params: { path: { quest_id: id } } })),
};

export default api;
