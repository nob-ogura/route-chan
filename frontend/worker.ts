export default {
	async fetch(request: Request, env: any): Promise<Response> {
		// まず静的アセットを試行
		const res = await env.ASSETS.fetch(request);
		if (res.status !== 404) return res;

		// ナビゲーション系（HTML）リクエストは index.html へフォールバック（SPA）
		const accept = request.headers.get("Accept") || "";
		if (accept.includes("text/html")) {
			const url = new URL(request.url);
			return env.ASSETS.fetch(
				new Request(new URL("/index.html", url).toString(), request),
			);
		}
		return res;
	},
} satisfies ExportedHandler<Env>;
