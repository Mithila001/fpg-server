import React, { useState, useEffect, useRef } from "react";
import { Stage, Layer, Circle, Text, Rect } from "react-konva";
import { Grid, Wall, Labels } from "./shapes";
import type { Coordinate, Label } from "./shapes";

interface CoordinateCanvasProps {
  // optional points array; component will fall back to a hardcoded set if none provided
  points?: Coordinate[];
  // array of textual labels to place on the stage
  labels?: Label[];
  // resolution multiplier; scales coordinates and grid spacing
  resolution?: number;
  // wall thickness in pixels
  wallThickness?: number;
}

const CoordinateCanvas: React.FC<CoordinateCanvasProps> = ({
  points,
  labels,
  resolution,
  wallThickness,
}) => {
  // default geometry in case caller doesn’t supply any coordinates
  const defaultPoints: Coordinate[] = [
    { x: 20, y: 20, label: "A" },
    { x: 120, y: 80, label: "B" },
    { x: 200, y: 150, label: "C" },
    { x: 20, y: 20, label: "D" },
  ];
  const effectivePoints = points && points.length > 0 ? points : defaultPoints;

  const scale = resolution ?? 1;
  const scaledPoints = effectivePoints.map((p) => ({
    x: p.x * scale,
    y: p.y * scale,
    label: p.label,
  }));

  const scaledLabels: Label[] | undefined = labels
    ? labels.map((l) => ({
        x: l.x * scale,
        y: l.y * scale,
        text: l.text,
        fontSize: l.fontSize,
        color: l.color,
      }))
    : undefined;

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // grid configuration
  const baseGridSize = 50;
  const gridSize = baseGridSize * scale; // pixels between lines, scaled

  // debug: log whenever dimensions state changes
  useEffect(() => {
    if (dimensions.width > 0 && dimensions.height > 0) {
      console.log(
        "Dimensions state updated:",
        Math.round(dimensions.width),
        "x",
        Math.round(dimensions.height),
        "scale:",
        scale,
      );
    }
  }, [dimensions, scale]);

  // watch the container's size and update dimensions for Konva
  useEffect(() => {
    const observeTarget = containerRef.current;
    if (!observeTarget) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
        console.log("CoordinateCanvas resized:", Math.round(width), "x", Math.round(height));
      }
    });

    resizeObserver.observe(observeTarget);

    return () => resizeObserver.unobserve(observeTarget);
  }, []);

  return (
    // minimal wrapper: this div is measured to provide dimensions
    // use full size so parent resizing triggers ResizeObserver
    <div ref={containerRef} style={{ width: "100%", height: "100%" }} className="bg-red-200">
      {dimensions.width > 0 && (
        <Stage width={Math.floor(dimensions.width)} height={Math.floor(dimensions.height)}>
          <Layer>
            {/* draw border around the entire canvas */}
            <Rect
              x={0}
              y={0}
              width={dimensions.width}
              height={dimensions.height}
              stroke="#000"
              strokeWidth={1}
            />

            {/* grid and labels */}
            <Grid dimensions={dimensions} gridSize={gridSize} />

            {/* walls rendered using the new Wall shape */}
            <Wall points={scaledPoints} thickness={wallThickness ?? 6} />

            {/* custom text labels */}
            {scaledLabels && <Labels labels={scaledLabels} />}

            {/* point markers / labels (keep for debugging) */}
            {scaledPoints.map((point, index) => (
              <React.Fragment key={index}>
                <Circle
                  x={point.x}
                  y={point.y}
                  radius={5}
                  fill="white"
                  stroke="#4f46e5"
                  strokeWidth={2}
                />
                <Text
                  x={point.x + 8}
                  y={point.y - 12}
                  text={point.label || `(${point.x}, ${point.y})`}
                  fontSize={11}
                  fontStyle="bold"
                  fill="#475569"
                />
              </React.Fragment>
            ))}
          </Layer>
        </Stage>
      )}
    </div>
  );
};

export default CoordinateCanvas;
