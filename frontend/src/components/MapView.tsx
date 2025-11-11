// frontend/src/components/MapView.tsx

import polyline from "@mapbox/polyline";
import L from "leaflet";
import { useEffect, useRef } from "react";
import type { LatLng } from "../types";

type Props = {
	depot: LatLng | null;
	locations: LatLng[];
	order: number[] | null;
	polylines: string[]; // polyline6
	onMapClick: (p: LatLng) => void;
};

const JP_CENTER: LatLng = { lat: 36.2048, lng: 138.2529 };

export default function MapView({
	depot,
	locations,
	order,
	polylines,
	onMapClick,
}: Props) {
	const mapRef = useRef<any>(null);
	const markersRef = useRef<any>(null);
	const routeRef = useRef<any>(null);
	const containerRef = useRef<HTMLDivElement | null>(null);

	// 初期化 + クリックハンドラ（onMapClick の最新を常に使う）
	useEffect(() => {
		// マップ未生成なら初期化
		if (!mapRef.current && containerRef.current) {
			const m = L.map(containerRef.current).setView(
				[JP_CENTER.lat, JP_CENTER.lng],
				5,
			);
			L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
				attribution:
					'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors',
			}).addTo(m);
			mapRef.current = m;
			markersRef.current = L.layerGroup().addTo(m);
			routeRef.current = L.layerGroup().addTo(m);
		}

		if (!mapRef.current) return;

		// クリックハンドラを最新の onMapClick に更新
		const handler = (e: any) =>
			onMapClick({ lat: e.latlng.lat, lng: e.latlng.lng });
		mapRef.current.off("click");
		mapRef.current.on("click", handler);
		return () => {
			mapRef.current?.off("click", handler);
		};
	}, [onMapClick]);

	// マーカー描画（depot + locations）
	useEffect(() => {
		if (!mapRef.current || !markersRef.current) return;
		const layer = markersRef.current;
		layer.clearLayers();

		const addNumberedMarker = (p: LatLng, label: string, color: string) => {
			const html = `<div style="background:${color};color:#fff;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;border:1px solid #fff;font-weight:bold;margin:0;padding:0;box-shadow:none;">${label}</div>`;
			const icon = L.divIcon({
				html,
				className: "",
				iconSize: [24, 24],
				iconAnchor: [12, 12],
			});
			L.marker([p.lat, p.lng], { icon }).addTo(layer);
		};

		if (depot) addNumberedMarker(depot, "出", "#1976d2");

		// 表示番号: 最適化前は追加順(1..N)、最適化後は order に基づく訪問順(1..N)
		if (order && order.length === locations.length) {
			order.forEach((locIdx, i) =>
				addNumberedMarker(locations[locIdx], String(i + 1), "#d32f2f"),
			);
		} else {
			locations.forEach((p, i) =>
				addNumberedMarker(p, String(i + 1), "#d32f2f"),
			);
		}
	}, [depot, locations, order]);

	// ルート描画（polyline6 -> LatLngs）
	useEffect(() => {
		if (!mapRef.current || !routeRef.current) return;
		const layer = routeRef.current;
		layer.clearLayers();
		polylines.forEach((pl) => {
			if (!pl) return;
			try {
				const latlngs = (polyline.decode(pl, 6) as [number, number][]).map(
					([lat, lng]: [number, number]) => [lat, lng],
				) as [number, number][];
				if (latlngs.length > 0) {
					L.polyline(latlngs, {
						color: "#1976d2",
						weight: 4,
						opacity: 0.8,
					}).addTo(layer);
				}
			} catch (_e) {
				// silently skip invalid polyline
			}
		});
	}, [polylines]);

	return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
