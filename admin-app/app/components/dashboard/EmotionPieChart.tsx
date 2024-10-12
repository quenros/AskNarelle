import React from 'react';
import { ResponsivePie } from '@nivo/pie';

interface PieChartProps {

    data: {
        "id": string,
        "label": string,
        "value": number,
        "color": string
    }[];
}

const EmotionsPieChart: React.FC<PieChartProps> =  ({ data }) => {
    console.log(data)
    return(
        <div className="h-96">
            <ResponsivePie
                data={data}
                margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
                innerRadius={0.5}
                padAngle={0.7}
                cornerRadius={3}
                activeOuterRadiusOffset={8}
                // colors={data.map(d => d.color)}
                borderWidth={1}
                borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
                arcLinkLabelsSkipAngle={10}
                arcLinkLabelsTextColor="#333333"
                arcLinkLabelsThickness={2}
                arcLinkLabelsColor={{ from: 'color' }}
                arcLabelsSkipAngle={10}
                arcLabelsTextColor={{
                    from: 'color',
                    modifiers: [
                        [
                            'darker',
                            2
                        ]
                    ]
                }}
                defs={[
                    {
                        id: 'dots',
                        type: 'patternDots',
                        background: 'inherit',
                        color: 'rgba(255, 255, 255, 0.3)',
                        size: 4,
                        padding: 1,
                        stagger: true
                    },
                    {
                        id: 'lines',
                        type: 'patternLines',
                        background: 'inherit',
                        color: 'rgba(255, 255, 255, 0.3)',
                        rotation: -45,
                        lineWidth: 6,
                        spacing: 10
                    }
                ]}
                fill={[
                    {
                        match: {
                            id: 'sadness'
                        },
                        id: 'dots'
                    },
                    {
                        match: {
                            id: 'joy'
                        },
                        id: 'dots'
                    },
                    {
                        match: {
                            id: 'love'
                        },
                        id: 'dots'
                    },
                    {
                        match: {
                            id: 'anger'
                        },
                        id: 'dots'
                    },
                    {
                        match: {
                            id: 'fear'
                        },
                        id: 'lines'
                    },
                    {
                        match: {
                            id: 'surprise'
                        },
                        id: 'lines'
                    },
                ]}
                legends={[
                    {
                        anchor: 'bottom',
                        direction: 'row',
                        justify: false,
                        translateX: 0,
                        translateY: 56,
                        itemsSpacing: 0,
                        itemWidth: 100,
                        itemHeight: 18,
                        itemTextColor: '#999',
                        itemDirection: 'left-to-right',
                        itemOpacity: 1,
                        symbolSize: 18,
                        symbolShape: 'circle',
                        effects: [
                            {
                                on: 'hover',
                                style: {
                                    itemTextColor: '#000'
                                }
                            }
                        ]
                    }
                ]}

            />
        </div>
      
    )
   
}

export default EmotionsPieChart;