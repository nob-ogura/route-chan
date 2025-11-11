// frontend/src/services/api.ts
import type { OptimizeRequest, OptimizeResponse } from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function health(): Promise<{ status: string }> {
	const r = await fetch(`${BASE}/api/health`);
	if (!r.ok) throw new Error(`health failed: ${r.status}`);
	return r.json();
}

export async function optimize(
	payload: OptimizeRequest,
): Promise<OptimizeResponse> {
	const r = await fetch(`${BASE}/api/optimize`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(payload),
	});
	const data = await r.json();
	if (!r.ok) {
		const msg = (data && (data.message || data.error)) || `status ${r.status}`;
		throw new Error(msg);
	}
	return data as OptimizeResponse;
}
