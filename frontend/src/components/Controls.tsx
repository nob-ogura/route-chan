// frontend/src/components/Controls.tsx
import { useState } from "react";
import * as api from "../services/api";
import type { LatLng } from "../types";

type Props = {
	depot: LatLng | null;
	locations: LatLng[];
	loading: boolean;
	error: string | null;
	onError: (m: string | null) => void;
	onReset: () => void;
	onOptimized: (r: {
		order: number[];
		polylines: string[];
		km: number;
	}) => void;
};

export default function Controls({
	depot,
	locations,
	loading,
	error,
	onError,
	onReset,
	onOptimized,
}: Props) {
	const [busy, setBusy] = useState(false);

	const optimize = async () => {
		onError(null);
		if (!depot || locations.length < 1) {
			onError("出発地点と訪問地点を設定してください。");
			return;
		}
		setBusy(true);
		try {
			const res = await api.optimize({ depot, locations });
			const km = Math.round((res.total_distance / 1000) * 10) / 10; // 小数1桁
			onOptimized({ order: res.route, polylines: res.route_geometries, km });
		} catch (e: any) {
			onError(e?.message ?? "最適化に失敗しました。");
		} finally {
			setBusy(false);
		}
	};

	return (
		<aside
			style={{
				borderLeft: "1px solid #e5e7eb",
				padding: "24px 20px",
				display: "flex",
				flexDirection: "column",
				gap: "16px",
				background: "#fafafa",
			}}
		>
			<div
				style={{
					fontSize: "18px",
					fontWeight: 700,
					color: "#1f2937",
					marginBottom: "4px",
				}}
			>
				操作
			</div>

		<button
			type="button"
			onClick={optimize}
			disabled={busy || loading}
			style={{
					padding: "12px 16px",
					fontSize: "15px",
					fontWeight: 600,
					color: "white",
					background:
						busy || loading
							? "#9ca3af"
							: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
					border: "none",
					borderRadius: "8px",
					cursor: busy || loading ? "not-allowed" : "pointer",
					boxShadow:
						busy || loading ? "none" : "0 2px 8px rgba(99, 102, 241, 0.25)",
					transition: "all 0.2s ease",
					transform: busy || loading ? "none" : "translateY(0)",
				}}
				onMouseEnter={(e) => {
					if (!busy && !loading) {
						e.currentTarget.style.transform = "translateY(-1px)";
						e.currentTarget.style.boxShadow =
							"0 4px 12px rgba(99, 102, 241, 0.35)";
					}
				}}
				onMouseLeave={(e) => {
					if (!busy && !loading) {
						e.currentTarget.style.transform = "translateY(0)";
						e.currentTarget.style.boxShadow =
							"0 2px 8px rgba(99, 102, 241, 0.25)";
					}
				}}
			>
				{busy ? "🔄 計算中…" : "🚀 最適化を実行"}
			</button>

		<button
			type="button"
			onClick={onReset}
			disabled={busy || loading}
			style={{
					padding: "10px 16px",
					fontSize: "14px",
					fontWeight: 500,
					color: busy || loading ? "#9ca3af" : "#6b7280",
					background: "white",
					border: "1px solid #e5e7eb",
					borderRadius: "8px",
					cursor: busy || loading ? "not-allowed" : "pointer",
					transition: "all 0.2s ease",
				}}
				onMouseEnter={(e) => {
					if (!busy && !loading) {
						e.currentTarget.style.background = "#f9fafb";
						e.currentTarget.style.borderColor = "#d1d5db";
					}
				}}
				onMouseLeave={(e) => {
					if (!busy && !loading) {
						e.currentTarget.style.background = "white";
						e.currentTarget.style.borderColor = "#e5e7eb";
					}
				}}
			>
				全消去
			</button>

			{(!depot || locations.length < 1) && (
				<div
					style={{
						color: "#92400e",
						background: "#fef3c7",
						padding: "12px 14px",
						borderRadius: "8px",
						border: "1px solid #fde68a",
						fontSize: "13px",
						lineHeight: "1.5",
						display: "flex",
						alignItems: "start",
						gap: "8px",
					}}
				>
					<span style={{ fontSize: "16px", flexShrink: 0 }}>⚠️</span>
					<span>Depot と訪問地点を設定してください。</span>
				</div>
			)}

			{error && (
				<div
					style={{
						color: "#991b1b",
						background: "#fee2e2",
						padding: "12px 14px",
						borderRadius: "8px",
						border: "1px solid #fecaca",
						fontSize: "13px",
						lineHeight: "1.5",
						display: "flex",
						alignItems: "start",
						gap: "8px",
					}}
				>
					<span style={{ fontSize: "16px", flexShrink: 0 }}>❌</span>
					<span>{error}</span>
				</div>
			)}

		<div
			style={{
				fontSize: "12px",
				color: "#6b7280",
				padding: "8px 12px",
				background: "white",
				borderRadius: "6px",
				border: "1px solid #e5e7eb",
				display: "flex",
				flexDirection: "column",
				gap: "6px",
			}}
		>
			<div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
				<span style={{ fontSize: "14px" }}>📍</span>
				<span style={{ fontWeight: 600 }}>使い方</span>
			</div>
			<div style={{ paddingLeft: "20px", lineHeight: "1.6" }}>
				1. 地図をクリックして出発地点を設定
				<br />
				2. さらにクリックして訪問地点を追加
				<br />
				3. 最適化ボタンを押下して経路を計算
			</div>
		</div>

		<div
			style={{
				fontSize: "12px",
				color: "#6b7280",
				padding: "8px 12px",
				background: "white",
				borderRadius: "6px",
				border: "1px solid #e5e7eb",
				display: "flex",
				alignItems: "center",
				gap: "6px",
			}}
		>
			<span style={{ fontSize: "14px" }}>ℹ️</span>
			<span>訪問地点の上限は 10 です。</span>
		</div>
		</aside>
	);
}
