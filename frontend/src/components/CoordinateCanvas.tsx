import React, { useState, useEffect, useRef } from "react";
import { Stage, Layer, Circle, Line, Text, Rect } from "react-konva";

interface Coordinate {
  x: number;
  y: number;
  label?: string;
}

interface CoordinateCanvasProps {
  // optional points array; component will fall back to a hardcoded set if none provided
  points?: Coordinate[];
  // resolution multiplier; scales coordinates and grid spacing
  resolution?: number;
}

const CoordinateCanvas: React.FC<CoordinateCanvasProps> = ({ points, resolution }) => {
  // default geometry in case caller doesn’t supply any coordinates
  const defaultPoints: Coordinate[] = [
    { x: 20, y: 20, label: "A" },
    { x: 120, y: 80, label: "B" },
    { x: 200, y: 150, label: "C" },
  ];
  const effectivePoints = points && points.length > 0 ? points : defaultPoints;

  const scale = resolution ?? 1;
  const scaledPoints = effectivePoints.map((p) => ({
    x: p.x * scale,
    y: p.y * scale,
    label: p.label,
  }));

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

  // build grid lines and labels when we know dimensions
  const renderGrid = () => {
    const elems: React.ReactNode[] = [];
    for (let x = 0; x <= dimensions.width; x += gridSize) {
      elems.push(
        <Line
          key={`v${x}`}
          points={[x, 0, x, dimensions.height]}
          stroke="#e0e0e0"
          strokeWidth={1}
        />,
      );
      elems.push(<Text key={`lx${x}`} x={x + 2} y={2} text={`${x}`} fontSize={10} fill="#999" />);
    }
    for (let y = 0; y <= dimensions.height; y += gridSize) {
      elems.push(
        <Line
          key={`h${y}`}
          points={[0, y, dimensions.width, y]}
          stroke="#e0e0e0"
          strokeWidth={1}
        />,
      );
      elems.push(<Text key={`ly${y}`} x={2} y={y + 2} text={`${y}`} fontSize={10} fill="#999" />);
    }
    return elems;
  };

  return (
    // minimal wrapper: this div is measured to provide dimensions
    // use full size so parent resizing triggers ResizeObserver
    <div ref={containerRef} style={{ width: "100%", height: "100%" }} className="bg-red-200">
      {dimensions.width > 0 && (
        <Stage width={dimensions.width} height={dimensions.height}>
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
            {renderGrid()}

            <Line
              points={scaledPoints.flatMap((p) => [p.x, p.y])}
              stroke="#6366f1"
              strokeWidth={3}
              lineCap="round"
              lineJoin="round"
              tension={0.2}
            />
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
