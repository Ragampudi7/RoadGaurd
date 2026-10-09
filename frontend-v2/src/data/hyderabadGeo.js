export const HYDERABAD_CENTER = { lat: 17.385, lng: 78.4867 };

export const TELANGANA_CENTER = { lat: 17.8496, lng: 79.1152 };

export const TELANGANA_BOUNDS = [
  [15.8, 77.1],
  [19.95, 81.35],
];

export const TELANGANA_OUTLINE = [
  [19.92, 78.16],
  [19.74, 78.29],
  [19.82, 78.48],
  [19.65, 78.67],
  [19.68, 78.88],
  [19.48, 79.01],
  [19.43, 79.26],
  [19.19, 79.32],
  [19.13, 79.61],
  [18.9, 79.68],
  [18.76, 79.93],
  [18.5, 80.02],
  [18.42, 80.27],
  [18.11, 80.34],
  [17.98, 80.62],
  [17.68, 80.64],
  [17.53, 80.46],
  [17.35, 80.55],
  [17.16, 80.35],
  [16.93, 80.28],
  [16.77, 80.03],
  [16.45, 79.96],
  [16.33, 79.72],
  [16.12, 79.58],
  [15.96, 79.33],
  [16.08, 79.08],
  [15.93, 78.86],
  [16.08, 78.62],
  [15.98, 78.37],
  [16.21, 78.18],
  [16.17, 77.91],
  [16.43, 77.75],
  [16.55, 77.48],
  [16.85, 77.42],
  [17.06, 77.21],
  [17.35, 77.28],
  [17.56, 77.12],
  [17.78, 77.32],
  [18.07, 77.27],
  [18.23, 77.49],
  [18.52, 77.45],
  [18.73, 77.63],
  [18.98, 77.55],
  [19.16, 77.76],
  [19.45, 77.72],
  [19.58, 77.98],
  [19.92, 78.16],
];

export const HYDERABAD_AREAS = [
  { name: "HITEC City, Hyderabad", lat: 17.4435, lng: 78.3772 },
  { name: "Gachibowli, Hyderabad", lat: 17.4401, lng: 78.3489 },
  { name: "Madhapur, Hyderabad", lat: 17.4483, lng: 78.3915 },
  { name: "Jubilee Hills, Hyderabad", lat: 17.4326, lng: 78.4071 },
  { name: "Banjara Hills, Hyderabad", lat: 17.4126, lng: 78.4483 },
  { name: "Secunderabad, Hyderabad", lat: 17.4399, lng: 78.4983 },
  { name: "Kukatpally, Hyderabad", lat: 17.4948, lng: 78.3996 },
  { name: "Ameerpet, Hyderabad", lat: 17.4375, lng: 78.4483 },
  { name: "Koti, Hyderabad", lat: 17.3852, lng: 78.4867 },
  { name: "Charminar, Hyderabad", lat: 17.3616, lng: 78.4747 },
];

export function isInsideTelangana(point) {
  if (!point) return false;
  const [[south, west], [north, east]] = TELANGANA_BOUNDS;
  return point.lat >= south && point.lat <= north && point.lng >= west && point.lng <= east;
}

export function formatCoordinates(point) {
  if (!point) return "";
  return `${point.lat.toFixed(4)} deg N, ${point.lng.toFixed(4)} deg E`;
}
