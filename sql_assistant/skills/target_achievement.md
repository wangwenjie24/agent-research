---
name: target_achievement
description: 目标达成的数据库 schema 和业务逻辑，包括月度/年度预算完成率，帮助领导判断生产进度是否符合预期。
---

# Target Achievement Schema

## Tables

### ps_daily_report
- id (PRIMARY KEY)
- report_date — 报告日期
- station_id (FOREIGN KEY -> ps_station)
- station_name — 场站名称
- monthly_generation — 月发电量（万 kWh）
- monthly_budget — 月度预算（万 kWh）
- monthly_budget_completion_rate — 月度预算完成率（%）
- yearly_generation — 年发电量（万 kWh）
- yearly_budget — 年度预算（万 kWh）
- yearly_budget_completion_rate — 年度预算完成率（%）

### ps_station
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_id (FOREIGN KEY -> ps_region)
- station_name — 场站名称
- station_type — 场站类型（光伏/风电）

### ps_region
- id (PRIMARY KEY)
- company_id (FOREIGN KEY -> ps_company)
- region_name — 区域名称

### ps_company
- id (PRIMARY KEY)
- company_name — 公司名称

## Business Logic

**预算完成率**：monthly_budget_completion_rate 和 yearly_budget_completion_rate 已在日报中直接记录，取最新日期的值即为当前进度。单位为百分比，0.8000 表示 80%。

**月度进度判断**：用当月已过天数占比与月度预算完成率对比。例如 4月2日，月度进度约 6.7%（2/30），若完成率已达 10% 则进度超前。

**年度进度判断**：用当年已过天数占比与年度预算完成率对比。

**区域/公司维度汇总**：预算字段需按区域或公司维度 SUM 聚合后再计算整体完成率，不能对 completion_rate 直接求平均。

**预算偏差量**：monthly_generation - monthly_budget 为正值表示超额完成，负值表示滞后。

**滞后预警**：月度完成率低于时间进度占比的区域/场站需要关注。

## Example Query

-- 各区域最新月度预算完成率
SELECT
    r.region_name,
    SUM(d.monthly_generation) AS actual_generation,
    SUM(d.monthly_budget) AS budget,
    SUM(d.monthly_generation) / NULLIF(SUM(d.monthly_budget), 0) AS completion_rate
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE d.report_date = '2026-04-02'
GROUP BY r.region_name
ORDER BY completion_rate ASC;

-- 预算达成最滞后的 Top5 场站
SELECT
    d.station_name,
    d.monthly_generation,
    d.monthly_budget,
    d.monthly_generation - d.monthly_budget AS gap,
    d.monthly_budget_completion_rate
FROM ps_daily_report d
WHERE d.report_date = '2026-04-02'
  AND d.monthly_budget IS NOT NULL
ORDER BY d.monthly_budget_completion_rate ASC
LIMIT 5;

-- 各区域年度预算进度 vs 时间进度
SELECT
    r.region_name,
    SUM(d.yearly_generation) AS yearly_actual,
    SUM(d.yearly_budget) AS yearly_budget,
    SUM(d.yearly_generation) / NULLIF(SUM(d.yearly_budget), 0) AS yearly_completion_rate,
    DAYOFYEAR('2026-04-02') / DAYOFYEAR('2026-12-31') AS time_progress
FROM ps_daily_report d
JOIN ps_station s ON d.station_id = s.id
JOIN ps_region r ON s.region_id = r.id
WHERE d.report_date = '2026-04-02'
GROUP BY r.region_name;
