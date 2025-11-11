// frontend/src/types/index.ts
export type LatLng = { lat: number; lng: number };

export type OptimizeRequest = {
	depot: LatLng;
	locations: LatLng[];
};

export type OptimizeResponse = {
	route: number[]; // locations のインデックス順
	total_distance: number; // meters
	route_geometries: string[]; // polyline6 の配列（各 leg）
};
