"use client";
import React, { ReactNode } from 'react';

interface CardDataStatsProps {
  title: string;
  total: number|undefined;
  rate: string;
  levelUp?: boolean;
  levelDown?: boolean;
  children: ReactNode;
}

const CardDataStats: React.FC<CardDataStatsProps> = ({
  title,
  total,
  rate,
  levelUp,
  levelDown,
  children,
}) => {
  return (
    <div className="flex rounded-sm border border-stroke bg-white py-6 px-7.5  shadow-md w-[300px] px-1 justify-around">
      <div className="h-11.5 w-11.5 rounded-full">
        {children}
      </div>

      <div className="flex items-end justify-between">
        <div>
          <h4 className="font-bold text-black text-lg md:text-2xl font-nunito">
            {total}
          </h4>
          <span className="text-sm font-medium text-[#2C3463] font-nunito">{title}</span>
        </div>
      </div>
    </div>
  );
};

export default CardDataStats;
