  // frontend/src/components/Summary.tsx
  import type { LatLng } from "../types";

  type Props = {
    depot: LatLng | null;
    locations: LatLng[];
    order: number[] | null; // locations のインデックス
    km?: number; // 必要なら App/Controls から渡す
  };

  export default function Summary({ depot, locations, order, km }: Props) {
    return (
      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        <div>Depot: {depot ? `${depot.lat.toFixed(4)}, ${depot.lng.toFixed(4)}` : "未設定"}</div>
        <div>地点数: {locations.length}</div>
        <div>
          訪問順序: {order && order.length > 0 ? order.map((i) => i + 1).join(" → ") : "未計算"}
        </div>
        {typeof km === "number" && <div>総距離: {km} km</div>}
      </div>
    );
  }
