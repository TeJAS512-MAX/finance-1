'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries } from 'lightweight-charts'

interface TradingChartProps {
  data: {
    time: string | number
    open: number
    high: number
    low: number
    close: number
  }[]
  symbol?: string
}

export default function TradingChart({ data, symbol = 'RELIANCE' }: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    // Create chart instance matching our terminal theme
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#2B2F3A', style: 1 }, // dotted/dashed
        horzLines: { color: '#2B2F3A', style: 1 },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#2B2F3A',
      },
      rightPriceScale: {
        borderColor: '#2B2F3A',
      },
      crosshair: {
        mode: 1, // Normal mode
        vertLine: { color: '#6B7280', labelBackgroundColor: '#1A1D24' },
        horzLine: { color: '#6B7280', labelBackgroundColor: '#1A1D24' },
      },
    })
    
    chartRef.current = chart

    // Add Candlestick series with our financial colors
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#2E9E66',
      downColor: '#CC4B4B',
      borderVisible: false,
      wickUpColor: '#2E9E66',
      wickDownColor: '#CC4B4B',
    })
    
    seriesRef.current = candlestickSeries
    
    // Set data and fit content
    candlestickSeries.setData(data as any)
    chart.timeScale().fitContent()

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data])

  return (
    <div className="w-full h-full relative group">
      {/* Watermark/Symbol overlay */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none opacity-20">
        <h2 className="text-4xl font-bold tracking-tighter text-text-muted">{symbol}</h2>
        <p className="text-xs font-mono text-text-muted">1D / NSE</p>
      </div>
      <div ref={chartContainerRef} className="w-full h-full" />
    </div>
  )
}
