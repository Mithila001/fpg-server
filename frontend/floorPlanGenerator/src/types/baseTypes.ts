// These interfaces define the data shapes for our API requests and responses.

export interface RoomIn {
  width: number;
  height: number;
}

export interface Boundary {
  width: number;
  height: number;
}

export interface LayoutRequest {
  boundary: Boundary;
  rooms: RoomIn[];
}

export interface RoomOut {
  id: number;
  width: number;
  height: number;
  x: number;
  y: number;
}
