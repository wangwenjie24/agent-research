---
name: anomaly_alert
description: 异常预警的数据库 schema 和业务逻辑，包括数据完整性校验和波动异常检测，帮助领导发现需要关注的问题。
---

# Anomaly Alert Schema

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
- installed_capacity — 装机容量（MW）
- operating_turbines — 风机运行台数
- faulty_turbines — 风机故障台数

## Business Logic

**区域合计 vs 场站求和校验**：对某日某区域，SUM(所有场站 daily_generation) 应等于该区域的汇总数据。若不等则存在数据一致性问题。

**异常偏低判断**：某日某场站发电量显著低于其近期平均水平。可用：当日值 < 近7天平均值 * 阈值（如 50%），或用标准差判断（当日值 < 平均值 - 2 * 标准差）。

**突降突增**：日环比变化幅度超过阈值。如 |当日 - 前日| / 前日 > 50% 视为突变。

**缺失数据检测**：在日期范围内，某些场站没有对应的日报记录。用日期序列 LEFT JOIN 日报表，缺失的记录 IS NULL。

**波动稳定性**：用 STDDEV(daily_generation) 衡量场站在一段时间内的波动程度，标准差越小越稳定。

**零发电异常**：装机容量 > 0 但 daily_generation = 0 或 NULL 的场站可能存在设备故障或数据采集问题。

**数据一致性**：ps_daily_report.station_name 应与 ps_station.station_name 一致，若不一致说明存在数据录入问题。

## Example Query

-- 检查缺失数据的日期和场站
WITH date_range AS (
    SELECT DATE('2026-04-01') + INTERVAL seq DAY AS report_date
    FROM (SELECT 0 AS seq UNION SELECT 1 UNION SELECT 2 UNION SELECT 3
          UNION SELECT 4 UNION SELECT 5 UNION SELECT 6) days
),
active_stations AS (
    SELECT id, station_name FROM ps_station
)
SELECT
    dr.report_date,
    s.station_name
FROM date_range dr
CROSS JOIN active_stations s
LEFT JOIN ps_daily_report d ON d.report_date = dr.report_date AND d.station_id = s.id
WHERE d.id IS NULL
ORDER BY dr.report_date, s.station_name;

-- 发电量异常偏低的场站（低于近7天平均值的50%）
SELECT
    curr.station_name,
    curr.report_date,
    curr.daily_generation,
    avg_stats.avg_generation,
    avg_stats.stddev_generation
FROM ps_daily_report curr
JOIN (
    SELECT
        station_id,
        AVG(daily_generation) AS avg_generation,
        STDDEV(daily_generation) AS stddev_generation
    FROM ps_daily_report
    WHERE report_date >= DATE_SUB('2026-04-02', INTERVAL 7 DAY)
      AND report_date < '2026-04-02'
    GROUP BY station_id
) avg_stats ON curr.station_id = avg_stats.station_id
WHERE curr.report_date = '2026-04-02'
  AND curr.daily_generation < avg_stats.avg_generation * 0.5;

-- 日环比突变检测（波动超过50%）
SELECT
    curr.station_name,
    curr.report_date,
    curr.daily_generation,
    prev.daily_generation AS prev_generation,
    ABS(curr.daily_generation - prev.daily_generation) / NULLIF(prev.daily_generation, 0) AS change_ratio
FROM ps_daily_report curr
JOIN ps_daily_report prev ON curr.station_id = prev.station_id
    AND prev.report_date = DATE_SUB(curr.report_date, INTERVAL 1 DAY)
WHERE curr.report_date = '2026-04-02'
  AND ABS(curr.daily_generation - prev.daily_generation) / NULLIF(prev.daily_generation, 0) > 0.5
ORDER BY change_ratio DESC;

-- 波动最稳定的场站（标准差最小）
SELECT
    d.station_name,
    AVG(d.daily_generation) AS avg_gen,
    STDDEV(d.daily_generation) AS stddev_gen
FROM ps_daily_report d
WHERE d.report_date >= DATE_SUB('2026-04-02', INTERVAL 30 DAY)
GROUP BY d.station_name
HAVING COUNT(*) >= 20
ORDER BY stddev_gen ASC
LIMIT 1;
