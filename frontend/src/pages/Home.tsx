import React from "react";
import CoordinateCanvas from "../components/Konva/KonvaCanvas";

const Home: React.FC = () => {
  const data = [
    { x: 50, y: 50, label: "Top-Left" },
    { x: 350, y: 50, label: "Top-Right" },
    { x: 350, y: 350, label: "Bottom-Right" },
    { x: 50, y: 350, label: "Bottom-Left" },
  ];
  return (
    // ensure this page fills the available space and never scrolls
    <div className="flex flex-col flex-1 min-h-0 h-full">
      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* Left */}
        <div className="bg-amber-200 flex-1 min-w-0 p-2">
          <CoordinateCanvas points={data} resolution={1} wallThickness={8} />
        </div>

        {/* Right*/}
        <div className="bg-green-200 w-64 flex-none p-8">Right Property Panel</div>
      </div>
    </div>
  );
};

export default Home;
