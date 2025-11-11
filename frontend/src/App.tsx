// frontend/src/App.tsx
import { useState } from "react";
import Controls from "./components/Controls";
import MapView from "./components/MapView";
import Summary from "./components/Summary";
import type { LatLng } from "./types";

export default function App() {
	const [depot, setDepot] = useState<LatLng | null>(null);
	const [locations, setLocations] = useState<LatLng[]>([]);
	const [order, setOrder] = useState<number[] | null>(null); // 最適化後の訪問順（locationsのインデックス）
	const [loading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [polylines, setPolylines] = useState<string[]>([]); // polyline6
	const [km, setKm] = useState<number | undefined>(undefined);

	const maxLocations = 10;

	const resetAll = () => {
		setDepot(null);
		setLocations([]);
		setOrder(null);
		setPolylines([]);
		setError(null);
		setKm(undefined);
	};

	return (
		<main
			style={{
				display: "grid",
				gridTemplateRows: "auto 1fr auto",
				height: "100dvh",
			}}
		>
			<header style={{ padding: 12, borderBottom: "1px solid #ddd" }}>
				<h1 style={{ margin: 0, fontSize: 20 }}>Route-chan</h1>
			</header>
			<section
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 320px",
					minHeight: 0,
				}}
			>
				<MapView
					depot={depot}
					locations={locations}
					order={order}
					polylines={polylines}
					onMapClick={(p) => {
						setError(null);
						if (!depot) {
							setDepot(p);
							return;
						}
						if (locations.length >= maxLocations) {
							setError(`訪問地点は最大 ${maxLocations} までです。`);
							return;
						}
						setLocations((xs) => [...xs, p]);
					}}
				/>
				<Controls
					depot={depot}
					locations={locations}
					loading={loading}
					error={error}
					onError={setError}
					onReset={resetAll}
					onOptimized={(payload) => {
						setOrder(payload.order);
						setPolylines(payload.polylines);
						setKm(payload.km);
					}}
				/>
			</section>
			<footer style={{ padding: 12, borderTop: "1px solid #eee" }}>
				<Summary depot={depot} locations={locations} order={order} km={km} />
			</footer>
		</main>
	);
}
