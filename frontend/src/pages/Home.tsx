import React, { useEffect, useRef, useState } from "react";
import CoordinateCanvas from "../components/CoordinateCanvas";

const Home: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      // avoid useless state updates which trigger layout changes and
      // cause the observer to fire again with slightly different values
      setSize((prev) => {
        const roundedW = Math.round(width);
        const roundedH = Math.round(height);
        if (Math.round(prev.w) === roundedW && Math.round(prev.h) === roundedH) {
          return prev; // no change
        }

        return { w: width, h: height };
      });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const data = [
    { x: 50, y: 50, label: "Start" },
    { x: 150, y: 200 },
    { x: 300, y: 100, label: "Peak" },
  ];

  return (
    // ensure this page fills the available space and never scrolls
    <div className="flex flex-col flex-1 min-h-0 h-full">
      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* Left */}
        <div className="bg-amber-200 flex-1 min-w-0 p-2">
          <CoordinateCanvas points={data} resolution={1} />
        </div>

        {/* Right*/}
        <div className="bg-green-200 w-64 flex-none p-8">Right Property Panel</div>
      </div>
    </div>
  );
};

export default Home;
