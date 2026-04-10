---
name: business_overview
description: 经营概况的数据库 schema 和业务逻辑，包括发电量、装机容量等全局关键指标，帮助领导快速掌握生产全局。
---

# Business Overview Schema

## Tables

### ps_company
- id (PRIMARY KEY)
- company_name — 公司名称
- company_code — 公司编码

### ps_region
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_name — 区域名称
- region_code — 区域编码

### ps_station
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_id (FOREIGN KEY -> ps_region)
- station_name — 场站名称
- station_code — 场站编码
- station_type — 场站类型（光伏/风电）

### ps_daily_report
- id (PRIMARY KEY)
- report_date — 报告日期
- station_id (FOREIGN KEY -> ps_station)
- station_name — 场站名称
- installed_capacity — 装机容量（MW）
- daily_generation — 日发电量（万 kWh）
- monthly_generation — 月发电量（万 kWh）
- yearly_generation — 年发电量（万 kWh）
- daily_avg_wind_speed — 日平均风速（m/s）
- daily_avg_irradiance — 日平均辐照（MJ/㎡）
- operating_turbines — 风机运行台数
- faulty_turbines — 风机故障台数

## Business Logic

**表关系**：ps_company -> ps_region -> ps_station -> ps_daily_report，查询时通过 station_id 关联日报与场站，通过 region_id 关联场站与区域，通过 company_id 关联区域/场站与公司。

**数据层级**：场站发电量是最小统计单元，记录在 ps_daily_report 中。其中 daily_generation 为当日发电量，monthly_generation 为本月截止到查询日期的累计发电量，yearly_generation 为本年截止到查询日期的累计发电量。

**区域发电量**：JOIN ps_station 获取 region_id，再 JOIN ps_region 获取 region_name，按区域 GROUP BY 汇总场站发电量。

**分公司总发电量**：各区域发电量之和。通过 station_id JOIN ps_station → ps_region → ps_company 关联到公司维度，再 SUM(daily_generation) 得到分公司总量。

**风电/光伏拆分**：通过 ps_station.station_type 区分，station_type = '风电' 或 '光伏'。

**装机容量**：installed_capacity 单位为 MW，发电量 daily_generation 单位为万 kWh，计算利用小时数时需注意单位换算。

**日均发电量**：指定时间范围内 SUM(daily_generation) / COUNT(DISTINCT report_date)。

## Example Query

-- 2026年4月2日各区域发电量汇总
SELECT
    r.region_name,
    SUM(d.daily_generation) AS total_generation
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE d.report_date = '2026-04-02'
GROUP BY r.region_name
ORDER BY total_generation DESC;

-- 2026年3月华北分公司日均发电量
SELECT
    SUM(d.daily_generation) / COUNT(DISTINCT d.report_date) AS avg_daily_generation
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
JOIN ps_company c ON r.company_id = c.id
WHERE c.company_name = '华北分公司'
  AND d.report_date >= '2026-03-01'
  AND d.report_date <= '2026-03-31';

-- 2026年4月2日风电与光伏发电量
SELECT
    s.station_type,
    SUM(d.daily_generation) AS total_generation
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
WHERE d.report_date = '2026-04-02'
GROUP BY s.station_type;

-- 2026年4月2日是否所有区域都有发电？
SELECT
    r.region_name,
    COALESCE(SUM(d.daily_generation), 0) AS total_generation,
    CASE 
        WHEN SUM(d.daily_generation) IS NULL OR SUM(d.daily_generation) = 0 THEN '无发电'
        ELSE '有发电'
    END AS generation_status
FROM ps_region r
LEFT JOIN ps_station s ON r.id = s.region_id
LEFT JOIN ps_daily_report d ON s.id = d.station_id AND d.report_date = '2026-04-02'
GROUP BY r.id, r.region_name
ORDER BY total_generation DESC;