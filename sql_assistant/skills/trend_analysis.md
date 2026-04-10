---
name: trend_analysis
description: 趋势研判的数据库 schema 和业务逻辑，包括环比变化、同比分析和多日趋势，帮助领导判断生产走势是否向好。
---

# Trend Analysis Schema

## Tables

### ps_station
- id (PRIMARY KEY)
- region_id (FOREIGN KEY -> ps_region)
- station_name — 场站名称
- station_type — 场站类型（光伏/风电）

### ps_region
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_name — 区域名称

### ps_daily_report
- id (PRIMARY KEY)
- report_date — 报告日期
- station_id (FOREIGN KEY -> ps_station)
- station_name — 场站名称
- daily_generation — 日发电量（万 kWh）
- daily_avg_wind_speed — 日平均风速（m/s）
- daily_avg_irradiance — 日平均辐照（MJ/㎡）

## Business Logic

**日环比**：当日发电量 - 前一日发电量。用 LAG(daily_generation) OVER (PARTITION BY station_id ORDER BY report_date) 获取前一日值。环比增长率 = (当日 - 前日) / 前日 * 100%。

**近 N 天趋势**：取最近 N 天的 daily_generation 时间序列。判断整体趋势可用：最后一天 vs 第一天的差值，或线性回归斜率。增长最快即差值/斜率最大。

**持续下降**：连续 N 天 daily_generation 逐日递减。可用 LAG 多次比较或计数连续下降天数。

**近 N 天平均增长率**：对每日环比增长率求 AVG，或用 (末日 - 首日) / 首日 / (N-1) 计算日均复合增长率。

**整体趋势判断**：比较最近一段时间（如7天）与前一段时间的平均发电量，上升则整体趋势向上，反之下跌。

**同比**：当年某日/某期与去年同一日/同一期对比。通过 DATE_SUB(report_date, INTERVAL 1 YEAR) 关联去年同期数据。同比增长率 = (今年 - 去年) / 去年 * 100%。

**同比区间对比**：如"4月前7天同比去年同期"，分别对两个时间区间 SUM(daily_generation) 再比较。

**同比正/负增长场站**：按场站计算同比增长率后，按正负分组列出。

## Example Query

-- 各场站日环比变化（4月2日 vs 4月1日）
SELECT
    d.station_name,
    d.report_date,
    d.daily_generation,
    LAG(d.daily_generation) OVER (PARTITION BY d.station_id ORDER BY d.report_date) AS prev_day_generation,
    d.daily_generation - LAG(d.daily_generation) OVER (PARTITION BY d.station_id ORDER BY d.report_date) AS `change`,
    (d.daily_generation - LAG(d.daily_generation) OVER (PARTITION BY d.station_id ORDER BY d.report_date))
        / NULLIF(LAG(d.daily_generation) OVER (PARTITION BY d.station_id ORDER BY d.report_date), 0) * 100 AS change_rate
FROM ps_daily_report d
WHERE d.report_date IN ('2026-04-01', '2026-04-02')
ORDER BY d.station_name, d.report_date;

-- 山西区域近7天发电量趋势
SELECT
    report_date,
    SUM(daily_generation) AS daily_total
FROM ps_daily_report
WHERE station_id IN (SELECT id FROM ps_station WHERE region_id = (SELECT id FROM ps_region WHERE region_name = '山西'))
  AND report_date >= DATE_SUB('2026-04-02', INTERVAL 6 DAY)
  AND report_date <= '2026-04-02'
GROUP BY report_date
ORDER BY report_date;

-- 同比去年单日发电量变化（分公司整体）
SELECT
    curr.report_date AS `current_date`,
    SUM(curr.daily_generation) AS current_gen,
    SUM(prev.daily_generation) AS last_year_gen,
    (SUM(curr.daily_generation) - SUM(prev.daily_generation)) / NULLIF(SUM(prev.daily_generation), 0) * 100 AS yoy_rate
FROM ps_daily_report curr
JOIN ps_daily_report prev ON curr.station_id = prev.station_id
    AND prev.report_date = DATE_SUB(curr.report_date, INTERVAL 1 YEAR)
WHERE curr.report_date = '2026-04-02'
GROUP BY curr.report_date;

-- 同比正增长和负增长场站
SELECT
    d.station_name,
    SUM(CASE WHEN d.report_date >= '2026-04-01' AND d.report_date <= '2026-04-07' THEN d.daily_generation END) AS curr_week,
    SUM(CASE WHEN d.report_date >= '2025-04-01' AND d.report_date <= '2025-04-07' THEN d.daily_generation END) AS last_year_week,
    (SUM(CASE WHEN d.report_date >= '2026-04-01' AND d.report_date <= '2026-04-07' THEN d.daily_generation END)
     - SUM(CASE WHEN d.report_date >= '2025-04-01' AND d.report_date <= '2025-04-07' THEN d.daily_generation END))
    / NULLIF(SUM(CASE WHEN d.report_date >= '2025-04-01' AND d.report_date <= '2025-04-07' THEN d.daily_generation END), 0) * 100 AS yoy_rate
FROM ps_daily_report d
GROUP BY d.station_name
ORDER BY yoy_rate DESC;
