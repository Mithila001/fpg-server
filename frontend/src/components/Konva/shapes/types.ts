export interface Coordinate {
  x: number;
  y: number;
  label?: string;
}

// simple label that can be placed anywhere on the stage
export interface Label {
  x: number;
  y: number;
  text: string;
  fontSize?: number;
  color?: string;
}
