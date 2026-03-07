import React from "react";
import { Text } from "react-konva";
import type { Label } from "./types";

interface LabelsProps {
  labels: Label[];
}

const Labels: React.FC<LabelsProps> = ({ labels }) => {
  return (
    <>
      {labels.map((lbl, idx) => (
        <Text
          key={idx}
          x={lbl.x}
          y={lbl.y}
          text={lbl.text}
          fontSize={lbl.fontSize ?? 14}
          fill={lbl.color ?? "#000"}
        />
      ))}
    </>
  );
};

export default Labels;
