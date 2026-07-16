---
title: M1 MVP 实现计划
status: active
owner:
last-reviewed: 2026-07-17
related: [FR-018, FR-019, FR-002, FR-001, FR-003, FR-004, FR-006, FR-007, FR-008, FR-010, FR-011, FR-015, FR-017, ADR-0005, ADR-0006, ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0012, ADR-0013, ADR-0014]
---

# M1 MVP 实现计划

> 多项目端到端 MVP：设区间 → 录名单 → 录多项目 → 全局贪心生 成 → CSV 导出 + 参数导出复用。
> TDD 驱动，原子化切分，尽早集成，branch 策略管理。

## 设计原则

1. **原子化可切分**：每个 epic 是可独立验证的最小单元，内部拆为 TDD 步骤。
2. **每步自动化测试**：每个 TDD 步骤必须有自动化测试，通不过测试不能进入下一步。
3. **TDD 模式**：Red（写失败测试）→ Green（最小实现通过）→ Refactor（重构保持绿灯）。
4. **尽早集成**：依赖拓扑决定实现顺序，垂直切片优先打通最窄端到端链路，再横向扩展。
5. **Branch 策略**：feature/ 单功能，integration/ 集成验证，从 feature/m1-mvp 分出，逐级合回。

## Branch 策略

```
main
 └── feature/m1-mvp                     ← M1 总集成分支
      ├── feature/m1-domain-models      ← Epic 1
      ├── integration/m1-models         ← 集成点 1（Epic 1 完成后）
      ├── feature/m1-holiday-api        ← Epic 2
      ├── integration/m1-models-holiday ← 集成点 2（Epic 1+2 集成）
      ├── feature/m1-generator-core     ← Epic 3
      ├── integration/m1-gen-holiday    ← 集成点 3（generator + holiday）
      ├── feature/m1-generator-multi    ← Epic 4
      ├── integration/m1-gen-multi      ← 集成点 4（多项目生成）
      ├── feature/m1-csv-export         ← Epic 5
      ├── integration/m1-gen-csv        ← 集成点 5（生成+CSV 端到端）
      ├── feature/m1-param-io           ← Epic 6
      ├── integration/m1-core-pipeline  ← 集成点 6（全核心管线无 UI）
      ├── feature/m1-ui-session         ← Epic 7
      ├── feature/m1-ui-input           ← Epic 8
      ├── feature/m1-ui-generate        ← Epic 9
      ├── feature/m1-ui-export          ← Epic 10
      ├── integration/m1-ui-assembly    ← 集成点 7（UI 集成）
      └── integration/m1-full-e2e       ← 集成点 8（最终 E2E，合回 main）
```

**规则**：
- feature 分支只做一个 epic，完成并测试全绿后合入对应 integration 分支。
- integration 分支合并后跑全量测试，全绿才能继续。
- integration 全部通过后合入 `feature/m1-mvp`。
- `feature/m1-mvp` 全部 epic 完成后合回 `main`。

## 依赖拓扑与实现顺序

```
Epic 1 domain models（零依赖）
  → Epic 2 holiday API client（依赖 models）
    → Epic 3 generator core 单人生成（依赖 models + holiday）
      → Epic 4 generator 多项目（依赖 Epic 3）
        → Epic 5 CSV exporter（依赖 models + generator 输出）
          → Epic 6 param importer/exporter（依赖 models）
            → Epic 7-10 UI（依赖以上所有）
              → E2E 集成
```

**垂直切片里程碑**：Epic 1+2+3+5 完成时即有一条"单人生成→CSV"的端到端链路可验证（无 UI，纯管线测试）。这是第一个可演示的集成点。

---

## Epic 1: Domain Models

**branch**: `feature/m1-domain-models`  
**集成到**: `integration/m1-models`  
**依赖**: 无  
**目标**: 实现所有领域数据模型（纯数据类 + 校验逻辑），零外部依赖。

### TDD 步骤

#### 1.1 Project 模型

**Red**: 写测试 `tests/test_models/test_project.py`
```python
def test_project_creation_with_required_fields():
    p = Project(id="p1", name="支付系统", start_date=date(2026,1,1),
                end_date=date(2026,3,31), target_ratio=0.3,
                required_job_types=["研发人员"], associated_person_ids=["u1"])
    assert p.id == "p1"
    assert p.target_ratio == 0.3

def test_project_invalid_ratio_raises():
    with pytest.raises(ValueError):
        Project(..., target_ratio=1.5, ...)

def test_project_empty_job_types_raises():
    with pytest.raises(ValueError):
        Project(..., required_job_types=[], ...)
```

**Green**: 实现 `src/timetable_generator/models/project.py`，最小代码通过测试。

**Refactor**: 提取校验逻辑到 `_validate()`。

#### 1.2 StaffChangeRecord 模型

**Red**: `tests/test_models/test_staff_change.py`
```python
def test_onboard_record():
    r = StaffChangeRecord(person_id="u1", date=date(2026,1,1),
                          type="onboard", job_type="研发人员", business_line=None)
    assert r.type == "onboard"

def test_leave_before_onboard_raises():
    # leave 日期早于 onboard → 在 service 层校验，model 只存
    pass
```

**Green**: 实现 `src/timetable_generator/models/staff_change.py`。

#### 1.3 WorkHourRecord 模型

**Red**: `tests/test_models/test_work_hour.py`
```python
def test_work_hour_record():
    r = WorkHourRecord(project_id="p1", person_id="u1",
                       date=date(2026,1,15), hours=8)
    assert r.hours == 8

def test_hours_must_be_integer_0_to_8():
    with pytest.raises(ValueError):
        WorkHourRecord(..., hours=9)
    with pytest.raises(ValueError):
        WorkHourRecord(..., hours=4.5)
```

**Green**: 实现 `src/timetable_generator/models/work_hour.py`。

#### 1.4 GlobalSpan + 默认值兜底推导

**Red**: `tests/test_models/test_staff_state.py`
```python
def test_default_fallback_active_span():
    span = GlobalSpan(start_date=date(2026,1,1), end_date=date(2026,6,30))
    state = StaffState.from_changes(person_id="u1", changes=[], global_span=span)
    assert state.active_span == (date(2026,1,1), date(2026,6,30))
    assert state.job_type == "研发人员"
    assert state.business_line is None

def test_with_onboard_leave():
    changes = [StaffChangeRecord("u1", date(2026,2,1), "onboard", "测试", "支付"),
               StaffChangeRecord("u1", date(2026,5,1), "leave")]
    state = StaffState.from_changes("u1", changes, span)
    assert state.active_span == (date(2026,2,1), date(2026,5,1))
    assert state.job_type == "测试"
```

**Green**: 实现 `src/timetable_generator/models/staff_state.py`（推导逻辑：从 changes 构建在职区间、工种、业务线；无 changes 用默认值）。

### Epic 1 验收

```bash
uv run pytest tests/test_models/ -v
```
全绿 → 合入 `integration/m1-models`。

---

## Epic 2: Holiday API Client

**branch**: `feature/m1-holiday-api`  
**集成到**: `integration/m1-models-holiday`（合并 Epic 1+2）  
**依赖**: Epic 1 (models)  
**目标**: 实现 timor.tech API 客户端 + 本地缓存 + 重试 3 次降级（ADR-0014）。

### TDD 步骤

#### 2.1 缓存层

**Red**: `tests/test_holiday/test_cache.py`
```python
def test_cache_save_and_load(tmp_path):
    cache = HolidayCache(cache_dir=tmp_path)
    cache.save_year(2026, {"2026-01-01": {"name": "元旦", "is_workday": False}})
    loaded = cache.load_year(2026)
    assert loaded["2026-01-01"]["is_workday"] is False

def test_cache_miss_returns_none(tmp_path):
    cache = HolidayCache(tmp_path)
    assert cache.load_year(2025) is None
```

**Green**: 实现 `src/timetable_generator/holiday/cache.py`（JSON 文件按年度存）。

#### 2.2 API 客户端 + 重试

**Red**: `tests/test_holiday/test_api_client.py`
```python
@pytest.mark.asyncio
async def test_fetch_year_success(httpx_mock):
    httpx_mock.get_response("http://timor.tech/api/holiday/year/2026",
                            json={"holiday": {"01-01": {...}}})
    client = HolidayApiClient()
    result = await client.fetch_year(2026)
    assert result is not None

@pytest.mark.asyncio
async def test_fetch_year_retry_3_then_none(httpx_mock):
    httpx_mock.get_response(..., status_code=500)  # 模拟 3 次失败
    client = HolidayApiClient(retry=3)
    result = await client.fetch_year(2026)
    assert result is None  # 降级信号
```

**Green**: 实现 `src/timetable_generator/holiday/api_client.py`（httpx + 重试 3 次返回 None）。

#### 2.3 降级模式：仅周末

**Red**: `tests/test_holiday/test_fallback.py`
```python
def test_fallback_weekend_only():
    resolver = HolidayResolver(holidays=None)  # 无节假日数据 → 降级
    assert resolver.is_workday(date(2026,1,5)) is False  # 周一？不，2026-01-05 是周二
    assert resolver.is_workday(date(2026,1,3)) is False   # 周六
    assert resolver.is_workday(date(2026,1,2)) is False   # 周五？检查日历
    # 降级模式：周一到五是工作日，周六日不是
    assert resolver.is_workday(date(2026,1,5)) is True   # 周二
    assert resolver.is_workday(date(2026,1,4)) is True   # 周日？不
    # 用明确的日期
    assert resolver.is_workday(date(2026,3,16)) is False  # 周一？检查
    # 实际测试用已知日期
```

**Green**: 实现 `src/timetable_generator/holiday/resolver.py`（有 holidays 用 API 数据，无 holidays 降级为仅周末判定）。

#### 2.4 集成：缓存优先 → API → 降级

**Red**: `tests/test_holiday/test_resolver_integration.py`
```python
@pytest.mark.asyncio
async def test_cache_hit_no_api_call(tmp_path, httpx_mock):
    cache = HolidayCache(tmp_path)
    cache.save_year(2026, {...})
    resolver = HolidayResolver(cache=cache, api_client=HolidayApiClient())
    await resolver.ensure_year(2026)
    # API 不应被调用
    httpx_mock.assert_not_called()

@pytest.mark.asyncio
async def test_api_fail_fallback_weekend(tmp_path, httpx_mock):
    httpx_mock.get_response(..., status_code=500)
    resolver = HolidayResolver(cache=HolidayCache(tmp_path), api_client=...)
    mode = await resolver.ensure_year(2026)
    assert mode == "fallback_weekend"
```

**Green**: 实现 `ensure_year` 编排逻辑（缓存 → API → 降级）。

### Epic 2 验收

```bash
uv run pytest tests/test_holiday/ -v
```
全绿 → 合入 `integration/m1-models-holiday`（合并 Epic 1+2，跑全量测试）。

---

## Epic 3: Generator Core（单人生成）

**branch**: `feature/m1-generator-core`  
**集成到**: `integration/m1-gen-holiday`  
**依赖**: Epic 1 + Epic 2  
**目标**: 实现启发式贪心生成器核心——单员工单项目的每日工时分配（ADR-0009）。

### TDD 步骤

#### 3.1 容量计算

**Red**: `tests/test_generator/test_capacity.py`
```python
def test_capacity_single_person():
    span = GlobalSpan(date(2026,1,1), date(2026,1,31))  # 1月
    staff_states = [StaffState.default("u1", span)]  # 全区间在职
    holidays = {date(2026,1,1)}  # 元旦
    capacity = compute_capacity(staff_states, holidays, span)
    # 1月工作日（扣元旦和周末）× 8h
    # 2026-01 有 22 个工作日（扣元旦后 21 个？需精确计算）
    assert capacity == 21 * 8  # 示例值，需精确
```

**Green**: 实现 `src/timetable_generator/generator/capacity.py`。

#### 3.2 比例换算

**Red**: `tests/test_generator/test_ratio.py`
```python
def test_target_hours_from_ratio():
    capacity = 1680  # 全员可用工时
    ratio = 0.3
    target = compute_target_hours(capacity, ratio)
    assert target == 504  # 1680 * 0.3
```

**Green**: 实现 `compute_target_hours`。

#### 3.3 贪心构造——单员工单项目

**Red**: `tests/test_generator/test_greedy_single.py`
```python
def test_single_person_single_project():
    span = GlobalSpan(date(2026,3,2), date(2026,3,13))  # 2周
    staff = [StaffState.default("u1", span)]
    project = Project("p1", "项目A", date(2026,3,2), date(2026,3,13),
                      target_ratio=1.0, required_job_types=["研发人员"],
                      associated_person_ids=["u1"])
    holidays = set()  # 无节假日
    records = generate(projects=[project], staff_states=staff,
                       holidays=holidays, global_span=span)
    # 每天 = 8h，10 个工作日（2周）
    assert sum(r.hours for r in records) == 10 * 8
    assert all(r.hours == 8 for r in records)  # 满载
    assert all(r.hours <= 8 for r in records)
```

**Green**: 实现贪心构造 `src/timetable_generator/generator/greedy.py`（单员工单项目：按工作日顺序填 8h 直到凑满 target）。

#### 3.4 满载 + 自然偏向抖动

**Red**: `tests/test_generator/test_jitter.py`
```python
def test_jitter_produces_natural_distribution():
    # 比例 < 1.0 时，不是所有工作日都分配
    # 分配的工作日应满载 8h，但有随机性（哪些天被选）
    records = generate(..., target_ratio=0.5, ...)
    assigned_days = {r.date for r in records}
    # 不是前一半日期（有随机性）
    # 但总工时 = target
    assert sum(r.hours for r in records) == target_hours
```

**Green**: 实现随机选择工作日 + 抖动逻辑。

#### 3.5 合规校验器

**Red**: `tests/test_generator/test_validator.py`
```python
def test_validate_all_pass():
    records = [WorkHourRecord("p1","u1",date(2026,3,2),8), ...]
    result = validate(records, projects, staff_states, holidays, span)
    assert result.is_valid
    assert result.violations == []

def test_validate_hours_exceed_8():
    records = [WorkHourRecord("p1","u1",date(2026,3,2),9)]  # 非法
    result = validate(records, ...)
    assert not result.is_valid
    assert any(v.rule == "hours_eq_8" for v in result.violations)

def test_validate_holiday_has_hours():
    records = [WorkHourRecord("p1","u1",date(2026,1,1),8)]  # 元旦有工时
    result = validate(records, ..., holidays={date(2026,1,1)})
    assert not result.is_valid

def test_validate_job_type_coverage():
    project = Project(..., required_job_types=["研发人员","测试"])
    records = [WorkHourRecord("p1","u1",...,8)]  # u1 是研发，无测试
    result = validate(records, [project], ...)
    assert not result.is_valid
    assert any(v.rule == "job_type_coverage" for v in result.violations)
```

**Green**: 实现 `src/timetable_generator/generator/validator.py`。

#### 3.6 N 次重试编排

**Red**: `tests/test_generator/test_retry.py`
```python
def test_retry_until_valid():
    # 模拟前几次贪心构造不通过校验，第 N 次通过
    call_count = 0
    def mock_greedy(...):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return invalid_records  # 故意不合规
        return valid_records
    result = generate_with_retry(..., greedy_fn=mock_greedy, max_retries=10)
    assert result.is_valid
    assert call_count == 3

def test_retry_exhausted_raises():
    def always_invalid(...):
        return invalid_records
    with pytest.raises(GenerationError):
        generate_with_retry(..., greedy_fn=always_invalid, max_retries=3)
```

**Green**: 实现 `generate_with_retry` 编排（贪心 → 校验 → 重试，N 次失败报错）。

#### 3.7 算法评估：Test Cases + Judge Function + Report

**目标**：对 generator core 做量化评估，验证算法效果可度量、可对比、可追踪。

**Red**: 写评估测试 `tests/test_generator/test_evaluation.py`

**Test Case 集合**（覆盖典型场景）：
```python
TEST_CASES = [
    # (id, 描述, 规模, 比例, 期望特征)
    ("tc_single_full", "单人全比例", 1人×10天, ratio=1.0, 每天满载8h),
    ("tc_single_half", "单人半比例", 1人×20天, ratio=0.5, 约半数天分配),
    ("tc_single_small", "小规模高精度", 1人×5天, ratio=0.3, 比例误差≤1h步长),
    ("tc_single_sparse", "低比例稀疏", 1人×30天, ratio=0.1, 分配天数少且分散),
    ("tc_single_jitter", "自然抖动", 1人×40天, ratio=0.6, 非机械连续),
]
```

**Judge Function**（多维度打分）：
```python
@dataclass
class JudgeScore:
    ratio_accuracy: float      # 比例达成度：1 - |实际比例 - 目标比例| / 目标比例
    hard_constraint_pass: bool # 硬约束全通过（=8h、节假日、工种覆盖）
    full_load_ratio: float     # 满载率：=8h的天数 / 分配天数（应为1.0）
    jitter_naturalness: float  # 抖动自然度：分配天分布的随机性评分（0=机械，1=自然）
    retry_count: int           # 重试次数（越少越好）
    overall_score: float       # 加权综合分

def judge(records, test_case, generation_result) -> JudgeScore:
    ...
```

**Evaluation Report**（自动生成）：
```python
def test_evaluation_report_generated(tmp_path):
    cases = run_all_test_cases(generator=generate)
    report = generate_eval_report(cases, output_path=tmp_path / "eval_report.md")
    assert report.path.exists()
    # 报告含：每个 test case 的 JudgeScore、硬约束通过率、平均比例误差、重试统计
    content = report.path.read_text()
    assert "ratio_accuracy" in content
    assert "hard_constraint_pass" in content
    assert "overall_score" in content
```

Report 格式（Markdown）：
```markdown
## Generator Core 评估报告

### 汇总
- 硬约束通过率：5/5 (100%)
- 平均比例误差：0.83%
- 平均重试次数：1.2
- 平均综合分：0.91

### 各 Test Case 详情
| Case | 规模 | 比例达成 | 满载率 | 自然度 | 重试 | 综合分 |
|---|---|---|---|---|---|---|
| tc_single_full | 1×10 | 100% | 1.0 | N/A | 1 | 1.00 |
| tc_single_half | 1×20 | 99.2% | 1.0 | 0.85 | 2 | 0.93 |
| ...

### 结论
- 硬约束：全通过 ✅
- 比例精度：1h 粒度下误差 ≤ 1h ✅
- 自然度：[评估]
- 是否可进入下一步：[是/否]
```

**Green**: 实现 `src/timetable_generator/generator/evaluation.py`（judge function + report 生成）。

**Refactor**: 提取 test case 定义到 `tests/test_generator/cases.py`，judge 逻辑到 `src/timetable_generator/generator/judge.py`。

### Epic 3 验收

```bash
uv run pytest tests/test_generator/ -v
uv run python -m timetable_generator.generator.evaluation --report  # 生成评估报告
```
全绿 + 评估报告硬约束通过率 100% + 比例误差 ≤ 1h → 合入 `integration/m1-gen-holiday`。

---

## Epic 4: Generator 多项目

**branch**: `feature/m1-generator-multi`  
**集成到**: `integration/m1-gen-multi`  
**依赖**: Epic 3  
**目标**: 扩展生成器支持多项目全局调度 + 1h 拆分 + 持续性策略（ADR-0005/0008/0010/0011）。

### TDD 步骤

#### 4.1 多项目跨日 =8h

**Red**: `tests/test_generator/test_multi_project.py`
```python
def test_two_projects_same_person_same_day():
    span = GlobalSpan(date(2026,3,2), date(2026,3,13))
    staff = [StaffState.default("u1", span)]
    p1 = Project("p1","A",..., target_ratio=0.5, ...)
    p2 = Project("p2","B",..., target_ratio=0.5, ...)
    records = generate([p1,p2], staff, holidays=set(), global_span=span)
    # 按日聚合，每人每天总和 = 8
    by_day = group_by_person_date(records)
    for (pid, day), day_records in by_day.items():
        assert sum(r.hours for r in day_records) == 8
```

**Green**: 扩展贪心支持多项目调度。

#### 4.2 1h 拆分

**Red**: `tests/test_generator/test_split.py`
```python
def test_1h_split_precision():
    # 小规模场景验证比例精确凑配
    span = GlobalSpan(date(2026,3,2), date(2026,3,6))  # 5天
    staff = [StaffState.default("u1", span)]
    p1 = Project("p1","A",..., target_ratio=0.3, ...)
    records = generate([p1], staff, ...)
    # 5 工作日 × 8h = 40h 分母，0.3 = 12h
    assert sum(r.hours for r in records) == 12
    # 12h 可拆为若干天的部分（如 3天×4h 或 2天×8h+1天×... ）
    # 但每天该项目分得 1h 整数倍
    assert all(r.hours % 1 == 0 for r in records)  # 整数小时
```

**Green**: 实现 1h 槽位分配逻辑。

#### 4.3 持续性策略

**Red**: `tests/test_generator/test_continuity.py`
```python
def test_continuous_block_min_3_days():
    # 验证连续参与 ≥3 天（软目标，统计性验证）
    span = GlobalSpan(date(2026,3,2), date(2026,4,10))  # 约6周
    records = generate(...)
    # 统计连续块长度，大部分应 ≥3
    blocks = compute_continuous_blocks(records, project_id="p1", person_id="u1")
    avg_block_len = mean(len(b) for b in blocks)
    assert avg_block_len >= 2.5  # 软目标，统计性

def test_split_refers_previous_day():
    # 验证拆分组合渐变（不剧变）
    records = generate([p1, p2], ...)
    # 相邻两天的同项目小时差 ≤ 2h
    for consecutive_days:
        diff = abs(day1_hours - day2_hours)
        assert diff <= 2
```

**Green**: 实现连续块优先 + 参考前一天策略。

#### 4.4 多项目冲突报错

**Red**: `tests/test_generator/test_conflict.py`
```python
def test_capacity_conflict_reports_person_and_projects():
    # 两个项目比例和 > 1.0 且只有一人
    p1 = Project(..., target_ratio=0.7, associated_person_ids=["u1"])
    p2 = Project(..., target_ratio=0.7, associated_person_ids=["u1"])
    with pytest.raises(GenerationError) as exc:
        generate([p1,p2], ...)
    assert "u1" in str(exc.value)
    assert "p1" in str(exc.value)
```

**Green**: 实现冲突检测与诊断报错。

#### 4.5 算法评估：多项目 Test Cases + Judge Function + Report

**目标**：对 generator multi 做量化评估，在 Epic 3 评估基础上增加多项目特有维度。

**Red**: 写评估测试 `tests/test_generator/test_evaluation_multi.py`

**多项目 Test Case 集合**（在 Epic 3 单人用例基础上扩展）：
```python
MULTI_TEST_CASES = [
    # (id, 描述, 规模, 项目数, 比例组合, 期望特征)
    ("tc_multi_2p_half", "2项目各50%", 1人×20天, 2项目, [0.5,0.5], 跨日=8h, 1h拆分),
    ("tc_multi_3p_split", "3项目拆分", 1人×30天, 3项目, [0.5,0.3,0.2], 每天拆分),
    ("tc_multi_2p_2person", "2项目2人", 2人×20天, 2项目, [0.4,0.3], 跨人跨项目),
    ("tc_multi_conflict", "容量冲突", 1人×10天, 2项目, [0.7,0.7], 应报错),
    ("tc_multi_continuity", "持续性验证", 1人×60天, 2项目, [0.6,0.4], 连续块≥3天),
    ("tc_multi_jitter_ref", "拆分渐变", 1人×30天, 2项目, [0.5,0.5], 相邻天差≤2h),
    ("tc_multi_precision", "小规模精度", 1人×5天, 2项目, [0.3,0.5], 1h精确凑配),
]
```

**多项目 Judge Function**（扩展 Epic 3 的 JudgeScore）：
```python
@dataclass
class MultiJudgeScore(JudgeScore):
    cross_project_eq_8h: bool       # 每人每天跨项目求和 = 8h（硬约束）
    split_1h_granularity: bool      # 所有分配为 1h 整数倍（硬约束）
    avg_block_length: float         # 平均连续块长度（软目标，应 ≥3）
    split_jitter_stability: float   # 拆分渐变稳定性：相邻天同项目小时差 ≤2h 的比例
    job_type_coverage: bool         # 每项目工种覆盖（硬约束）

def judge_multi(records, test_case, generation_result) -> MultiJudgeScore:
    ...
```

**Evaluation Report**（扩展，含多项目维度）：
```python
def test_multi_eval_report(tmp_path):
    cases = run_all_multi_cases(generator=generate)
    report = generate_eval_report(cases, output_path=tmp_path / "eval_multi.md")
    content = report.path.read_text()
    # 多项目特有维度
    assert "cross_project_eq_8h" in content
    assert "avg_block_length" in content
    assert "split_jitter_stability" in content
```

Report 格式（Markdown，扩展 Epic 3 格式）：
```markdown
## Generator Multi 评估报告

### 汇总
- 硬约束通过率：7/7 (100%)
  - 跨项目 =8h：100%
  - 1h 粒度：100%
  - 工种覆盖：100%
- 平均比例误差：0.92%
- 平均连续块长度：4.3 天（目标 ≥3）
- 拆分渐变稳定性：87%（相邻天差 ≤2h）
- 平均重试次数：2.1
- 平均综合分：0.88

### 各 Test Case 详情
| Case | 规模 | 跨日=8h | 1h粒度 | 连续块 | 渐变稳定 | 比例达成 | 重试 | 综合分 |
|---|---|---|---|---|---|---|---|---|
| tc_multi_2p_half | 1×20 | ✅ | ✅ | 5.2 | 95% | 99.5% | 1 | 0.95 |
| tc_multi_continuity | 1×60 | ✅ | ✅ | 4.3 | 82% | 98.7% | 3 | 0.86 |
| ...

### 冲突场景
| Case | 预期 | 实际 | 结论 |
|---|---|---|---|
| tc_multi_conflict | 报错+诊断 | 报错含u1/p1/p2 | ✅ |

### 结论
- 硬约束：全通过 ✅
- 持续性软目标：平均块 4.3 ≥ 3 ✅
- 拆分渐变：87% ≤ 阈值 [评估]
- 是否可进入下一步：[是/否]
```

**Green**: 扩展 `src/timetable_generator/generator/evaluation.py`（多项目 judge + report）。

**Refactor**: 统一单人/多项目评估为同一框架，test case 用标签区分。

### Epic 4 验收

```bash
uv run pytest tests/test_generator/ -v
uv run python -m timetable_generator.generator.evaluation --report --multi  # 生成多项目评估报告
```
全绿 + 评估报告硬约束通过率 100% + 跨项目 =8h 全通过 + 平均连续块 ≥3 + 比例误差 ≤ 1h → 合入 `integration/m1-gen-multi`。

---

## Epic 5: CSV Exporter

**branch**: `feature/m1-csv-export`  
**集成到**: `integration/m1-gen-csv`  
**依赖**: Epic 1 (models)  
**目标**: 实现 CSV 导出（项目-员工-日期-工时），FR-008。

### TDD 步骤

#### 5.1 CSV 序列化

**Red**: `tests/test_export/test_csv.py`
```python
def test_csv_export_basic(tmp_path):
    records = [
        WorkHourRecord("p1","张三",date(2026,3,2),8),
        WorkHourRecord("p1","张三",date(2026,3,3),4),
        WorkHourRecord("p2","张三",date(2026,3,3),4),
    ]
    path = tmp_path / "output.csv"
    export_csv(records, path)
    content = path.read_text()
    assert "项目,员工,日期,工时" in content
    assert "p1,张三,2026-03-02,8" in content
    assert "p2,张三,2026-03-03,4" in content

def test_csv_date_format():
    # 日期必须 YYYY-MM-DD
    records = [WorkHourRecord("p1","u1",date(2026,3,2),8)]
    path = tmp_path / "test.csv"
    export_csv(records, path)
    assert "2026-03-02" in path.read_text()
```

**Green**: 实现 `src/timetable_generator/export/csv.py`。

#### 5.2 端到端生成→CSV

**Red**: `tests/test_export/test_gen_to_csv.py`
```python
def test_generate_then_export(tmp_path):
    span = GlobalSpan(date(2026,3,2), date(2026,3,13))
    staff = [StaffState.default("u1", span)]
    project = Project("p1","A",..., target_ratio=1.0, ...)
    records = generate([project], staff, holidays=set(), global_span=span)
    path = tmp_path / "e2e.csv"
    export_csv(records, path)
    # 验证 CSV 行数 = 记录数 + 1（表头）
    lines = path.read_text().strip().split("\n")
    assert len(lines) == len(records) + 1
```

**Green**: 验证端到端管线。

### Epic 5 验收

```bash
uv run pytest tests/test_export/ -v
```
全绿 → 合入 `integration/m1-gen-csv`（Epic 1-5 集成，**第一个垂直切片里程碑：生成→CSV 端到端可验证**）。

---

## Epic 6: Param Importer/Exporter

**branch**: `feature/m1-param-io`  
**集成到**: `integration/m1-core-pipeline`  
**依赖**: Epic 1 (models)  
**目标**: 实现参数导出复用（项目+人事参数 → JSON，下次导入），ADR-0012 / FR-017。

### TDD 步骤

#### 6.1 参数序列化

**Red**: `tests/test_param_io/test_export.py`
```python
def test_export_session_params(tmp_path):
    session = SessionParams(
        global_span=GlobalSpan(date(2026,1,1), date(2026,6,30)),
        projects=[Project("p1",...)],
        staff=[StaffInfo("u1","张三",annual_leave_days=0)],
    )
    path = tmp_path / "params.json"
    export_params(session, path)
    data = json.loads(path.read_text())
    assert data["global_span"]["start_date"] == "2026-01-01"
    assert data["projects"][0]["id"] == "p1"

def test_import_params(tmp_path):
    # 导出再导入 = 往返一致
    session = SessionParams(...)
    path = tmp_path / "params.json"
    export_params(session, path)
    loaded = import_params(path)
    assert loaded == session
```

**Green**: 实现 `src/timetable_generator/io/params.py`（JSON 序列化/反序列化）。

#### 6.2 CSV 人事导入

**Red**: `tests/test_param_io/test_staff_import.py`
```python
def test_import_staff_csv(tmp_path):
    csv_content = "姓名,工种,业务线,年假额度\n张三,研发人员,,0\n李四,测试,支付,5"
    path = tmp_path / "staff.csv"
    path.write_text(csv_content)
    staff = import_staff_csv(path)
    assert len(staff) == 2
    assert staff[0].name == "张三"
    assert staff[0].job_type == "研发人员"
    assert staff[1].annual_leave_days == 5
```

**Green**: 实现 `import_staff_csv`。

### Epic 6 验收

```bash
uv run pytest tests/test_param_io/ -v
```
全绿 → 合入 `integration/m1-core-pipeline`（Epic 1-6 集成，**核心管线全通无 UI**）。

---

## Epic 7: UI — 会话与全局区间

**branch**: `feature/m1-ui-session`  
**集成到**: `integration/m1-ui-assembly`  
**依赖**: Epic 1 (models)  
**目标**: NiceGUI 会话初始化 UI——空会话、全局区间设定（ADR-0006/0013）。

### TDD 步骤

#### 7.1 会话状态管理

**Red**: `tests/test_ui/test_session_state.py`
```python
def test_session_starts_empty():
    session = SessionState()
    assert session.global_span is None
    assert session.projects == []
    assert session.staff == []

def test_set_global_span():
    session = SessionState()
    session.set_span(date(2026,1,1), date(2026,6,30))
    assert session.global_span.start_date == date(2026,1,1)
```

**Green**: 实现 `src/timetable_generator/ui/session.py`。

#### 7.2 全局区间 UI 组件

**Red**: `tests/test_ui/test_span_ui.py`（NiceGUI user_simulation）
```python
async def test_span_input(user):
    await user.open("/")
    # 输入起止日期
    # 验证 session.global_span 被设置
```

**Green**: 实现区间输入组件。

### Epic 7 验收

```bash
uv run pytest tests/test_ui/test_session*.py -v
```

---

## Epic 8: UI — 员工与项目录入

**branch**: `feature/m1-ui-input`  
**集成到**: `integration/m1-ui-assembly`  
**依赖**: Epic 7  
**目标**: 员工名单 UI + 多项目批次录入 UI。

### TDD 步骤

#### 8.1 员工名单表格

**Red**: `tests/test_ui/test_staff_input.py`
```python
async def test_add_staff_member(user):
    await user.open("/")
    # 添加员工"张三"，默认工种"研发人员"
    # 验证 session.staff 含张三

async def test_staff_default_job_type(user):
    # 不填工种 → 默认"研发人员"
```

#### 8.2 项目录入表单

**Red**: `tests/test_ui/test_project_input.py`
```python
async def test_add_project(user):
    # 录入项目：标识、起止日期、比例、工种、关联员工
    # 验证 session.projects 含该项目

async def test_add_multiple_projects(user):
    # 录入两个项目
    # 验证 session.projects 长度 = 2
```

**Green**: 实现员工表格 + 项目表单组件。

### Epic 8 验收

```bash
uv run pytest tests/test_ui/test_staff*.py tests/test_ui/test_project*.py -v
```

---

## Epic 9: UI — 生成与进度

**branch**: `feature/m1-ui-generate`  
**集成到**: `integration/m1-ui-assembly`  
**依赖**: Epic 8 + Epic 3/4 (generator)  
**目标**: 生成按钮 + 异步执行 + 进度反馈 + 结果摘要（ADR-0009 D5 / ADR-0013 D2）。

### TDD 步骤

#### 9.1 生成触发 + 异步

**Red**: `tests/test_ui/test_generate.py`
```python
async def test_generate_button_triggers_generation(user):
    # 录入完整输入 → 点击生成
    # 验证 session.results 非空

async def test_generation_does_not_block_ui(user):
    # 生成过程中 UI 仍可交互（进度可见）
```

#### 9.2 进度反馈

**Red**: `tests/test_ui/test_progress.py`
```python
async def test_progress_displayed_during_generation(user):
    # 生成时显示"正在生成... 第 N/M 轮"
    # 验证进度元素存在
```

#### 9.3 结果摘要 + 降级提示

**Red**: `tests/test_ui/test_results.py`
```python
async def test_results_summary_shown(user):
    # 生成完成后显示总工时、比例达成度
    # 验证摘要元素

async def test_holiday_fallback_warning(user):
    # 节假日降级时显示提示
    # 验证提示元素
```

**Green**: 实现生成编排 + 进度 + 摘要 + 降级提示。

### Epic 9 验收

```bash
uv run pytest tests/test_ui/test_generate*.py tests/test_ui/test_progress*.py tests/test_ui/test_results*.py -v
```

---

## Epic 10: UI — 导出

**branch**: `feature/m1-ui-export`  
**集成到**: `integration/m1-ui-assembly`  
**依赖**: Epic 9 + Epic 5 (CSV) + Epic 6 (param IO)  
**目标**: CSV 导出按钮 + 参数导出/导入按钮（FR-008 / ADR-0012）。

### TDD 步骤

#### 10.1 CSV 导出

**Red**: `tests/test_ui/test_export_ui.py`
```python
async def test_csv_download(user):
    # 生成后点击"导出 CSV"
    # 验证下载触发（文件存在或下载事件触发）

async def test_export_disabled_before_generation(user):
    # 未生成时导出按钮禁用
```

#### 10.2 参数导出/导入

**Red**: `tests/test_ui/test_param_io_ui.py`
```python
async def test_export_params(user):
    # 录入后点击"导出配置"
    # 验证文件生成

async def test_import_params(user):
    # 导入配置文件
    # 验证 session 被填充
```

**Green**: 实现导出/导入 UI 按钮。

### Epic 10 验收

```bash
uv run pytest tests/test_ui/test_export*.py tests/test_ui/test_param_io*.py -v
```

---

## 最终集成

**branch**: `integration/m1-full-e2e`  
**目标**: 全量集成测试，验证 M1 MVP 完整端到端流程。

### E2E 测试

**Red**: `tests/test_e2e/test_m1_full.py`
```python
async def test_full_m1_flow(user):
    """完整 M1 流程：设区间 → 录名单 → 录多项目 → 生成 → 导出 CSV"""
    await user.open("/")
    # 1. 设全局区间
    # 2. 添加员工
    # 3. 添加两个项目
    # 4. 点击生成
    # 5. 验证结果摘要
    # 6. 导出 CSV
    # 7. 验证 CSV 内容

async def test_full_m1_param_roundtrip(user):
    """参数导出 → 重新导入 → 生成结果一致"""
    # 录入 → 导出参数 → 清空 → 导入参数 → 生成 → 导出 CSV
    # 验证两次 CSV 内容一致（或工时总量一致）

def test_full_m1_cli_pipeline():
    """无 UI 端到端：纯管线测试"""
    span = GlobalSpan(date(2026,1,1), date(2026,3,31))
    staff = [StaffState.default("u1", span), StaffState.default("u2", span)]
    projects = [
        Project("p1","支付",..., target_ratio=0.3, required_job_types=["研发人员"], ...),
        Project("p2","风控",..., target_ratio=0.2, required_job_types=["研发人员"], ...),
    ]
    records = generate(projects, staff, holidays=holidays, global_span=span)
    result = validate(records, projects, staff, holidays, span)
    assert result.is_valid
    export_csv(records, Path("/tmp/m1_e2e.csv"))
```

### 最终验收

```bash
uv run pytest -v  # 全量测试全绿
uv run ruff check .
uv run ruff format --check .
```

全绿 → `integration/m1-full-e2e` 合入 `feature/m1-mvp` → 合回 `main`。

---

## 集成里程碑速查

| 集成点 | branch | 内容 | 里程碑意义 |
|---|---|---|---|
| 1 | integration/m1-models | Epic 1 | 数据模型可验证 |
| 2 | integration/m1-models-holiday | Epic 1+2 | + 节假日 |
| 3 | integration/m1-gen-holiday | Epic 1+2+3 | + 单人生成 |
| 4 | integration/m1-gen-multi | Epic 1-4 | + 多项目生成 |
| 5 | integration/m1-gen-csv | Epic 1-5 | **垂直切片：生成→CSV 端到端** |
| 6 | integration/m1-core-pipeline | Epic 1-6 | **核心管线全通（无 UI）** |
| 7 | integration/m1-ui-assembly | Epic 7-10 | UI 集成 |
| 8 | integration/m1-full-e2e | 全部 | **M1 完整端到端，合回 main** |
