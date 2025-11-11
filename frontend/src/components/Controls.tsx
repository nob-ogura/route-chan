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
    onOptimized: (r: { order: number[]; polylines: string[]; km: number }) => void;
  };

  export default function Controls({ depot, locations, loading, error, onError, onReset, onOptimized }: Props) {
    const [busy, setBusy] = useState(false);

    const optimize = async () => {
      onError(null);
      if (!depot || locations.length < 1) {
        onError("Depot と訪問地点を設定してください。");
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
      <aside style={{ borderLeft: "1px solid #eee", padding: 12, display: "grid", gap: 8 }}>
        <div style={{ fontWeight: 600 }}>操作</div>
        <button onClick={optimize} disabled={busy || loading}>
          {busy ? "計算中…" : "最適化を実行"}
        </button>
        <button onClick={onReset} disabled={busy || loading}>全消去</button>
        {(!depot || locations.length < 1) && (
          <div style={{ color: "#b26a00", background: "#fff3cd", padding: 8, border: "1px solid #ffeeba" }}>
            Depot と訪問地点を設定してください。
          </div>
        )}
        {error && (
          <div style={{ color: "#842029", background: "#f8d7da", padding: 8, border: "1px solid #f5c2c7" }}>
            {error}
          </div>
        )}
        <div style={{ fontSize: 12, color: "#666" }}>
          訪問地点の上限は 10 です。
        </div>
      </aside>
    );
  }
