---
name: performance_benchmarking
description: 绩效对标的数据库 schema 和业务逻辑，包括区域/场站排名、贡献占比和横向对比，帮助领导评估各组织单元的相对表现。
---

# Performance Benchmarking Schema

## Tables

### ps_company
- id (PRIMARY KEY)
- company_name — 公司名称

### ps_region
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_name — 区域名称

### ps_station
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_id (FOREIGN KEY -> ps_region)
- station_name — 场站名称
- station_type — 场站类型（光伏/风电）

### ps_daily_report
- id (PRIMARY KEY)
- report_date — 报告日期
- station_id (FOREIGN KEY -> ps_station)
- station_name — 场站名称
- daily_generation — 日发电量（万 kWh）
- monthly_generation — 月发电量（万 kWh）
- yearly_generation — 年发电量（万 kWh）
- installed_capacity — 装机容量（MW）

## Business Logic

**贡献占比**：某区域（或场站）发电量 / 公司总发电量。总发电量为所有场站 SUM(daily_generation)。

**Top N 排名**：按发电量降序排列取前 N。用 ROW_NUMBER() 或 ORDER BY + LIMIT 实现。

**区域对比**：两区域发电量相减得差值，相除得倍数关系。

**区域内场站排名**：WHERE region_id = X 后按发电量排序。

**贡献最大/最小**：贡献占比最高即贡献最大，最低即贡献最小。

**装机利用率对比**：发电量 / installed_capacity 可消除装机规模差异，更公平地对比不同规模场站的效率。

**月度/年度排名**：使用 monthly_generation 或 yearly_generation 字段直接排序，无需逐日累加。

## Example Query

-- 2026年3月各区域发电量排名及贡献占比
SELECT
    r.region_name,
    SUM(d.monthly_generation) AS total_generation,
    SUM(d.monthly_generation) / (
        SELECT SUM(monthly_generation)
        FROM ps_daily_report
        WHERE report_date = '2026-03-31'
    ) AS contribution_rate
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE d.report_date = '2026-03-31'
GROUP BY r.region_name
ORDER BY total_generation DESC;

-- 山东区域内发电量排名前3的场站
SELECT
    d.station_name,
    d.monthly_generation
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE r.region_name = '山东'
  AND d.report_date = '2026-03-31'
ORDER BY d.monthly_generation DESC
LIMIT 3;

-- 山西和山东区域发电量对比
SELECT
    r.region_name,
    SUM(d.daily_generation) AS total_generation
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE r.region_name IN ('山西', '山东')
  AND d.report_date = '2026-04-02'
GROUP BY r.region_name;
