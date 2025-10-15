# 空气质量时空分析实训

本项目通过公开环境监测数据（OpenAQ）与地理信息分析（GeoPandas、Folium），完成以下任务：
- 数据采集（PM2.5、SO₂、NO₂，含经纬度与时间）
- 空间分布图（PM2.5热力图）
- 超阈值自动预警
- 时间变化趋势分析（季节、昼夜）

## 快速开始

1) 创建并激活虚拟环境（可选）
```bash
python -m venv .venv && source .venv/bin/activate
```

2) 安装依赖
```bash
pip install -r requirements.txt
```

3) 运行分析（示例：北京最近数据，拉取最多3页）
```bash
python -m src.aq_analyzer.cli --city Beijing --country CN --parameters pm25 so2 no2 --max_pages 3 --out_prefix outputs/beijing
```

输出：
- `outputs/maps/pm25_heatmap.html`
- `outputs/plots/trends_monthly.png` 与 `outputs/plots/trends_diurnal.png`
- `outputs/alerts/alerts.csv`
- `outputs/beijing_data.csv`

## 预警阈值示例
- PM2.5>150 重度污染
- SO₂>350 预警
- NO₂>200 预警

可通过参数覆盖：
```bash
python -m src.aq_analyzer.cli --pm25_thr 150 --so2_thr 350 --no2_thr 200
```

## 注意
- OpenAQ 接口存在速率限制，已设置分页与间隔。
- 若数据为空，检查时间范围、城市/国家、或扩大查询范围（如使用 `--bbox`）。
