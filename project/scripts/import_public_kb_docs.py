import json
import urllib.request


BASE = "http://127.0.0.1:18888/api"


def request_json(path, method="GET", payload=None, token=None):
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["X-Auth-Token"] = token
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    login = request_json("/auth/login", "POST", {"username": "admin", "password": "admin123"})
    token = login["data"]["token"]

    existing = request_json("/kb/docs", token=token)["data"]
    for doc in existing:
        title = doc.get("title") or ""
        if "?" in title or title.startswith("????"):
            request_json(f"/kb/docs/{doc['id']}", "DELETE", token=token)
    existing_titles = {
        (doc.get("title") or "")
        for doc in request_json("/kb/docs", token=token)["data"]
    }

    docs = [
        {
            "title": "公开资料整理：RevPAR、ADR、入住率联动看板口径",
            "content": """分类：REVENUE / 指标口径
来源：SiteMinder RevPAR 说明 https://www.siteminder.com/r/calculate-revpar/；Cloudbeds 收益管理指标说明 https://www.cloudbeds.com/revenue-management/

核心口径：
- 入住率只说明房间卖出了多少，ADR 只说明卖出房间的平均价格，二者单独看都不足以判断经营质量。
- RevPAR = ADR × 入住率，也可以用客房收入 ÷ 可售房间数计算。
- 当入住率上升但 RevPAR 没有同步改善时，通常需要检查低价渠道、折扣房型和团队房占比。
- 当 ADR 上升但入住率明显下滑时，可能意味着价格超过市场需求，需要结合竞品、节假日、活动和取消率判断。

系统落地规则：
- 经营总览同时展示入住、营收、取消率，避免单一指标误判。
- 预测分析页输出当前值、预测值、变化幅度，值班经理据此决定是否调价、控房或增派人手。
- 数据管理页录入历史日指标时，应保持入住率、营收、取消率、评分、差评率口径一致。

可检索问题示例：RevPAR 怎么判断？入住率上涨但营收没有上涨怎么办？为什么不能只看 ADR？""",
        },
        {
            "title": "公开资料整理：酒店收益管理与需求预测处置清单",
            "content": """分类：REVENUE / 预测处置
来源：Cloudbeds Hotel Revenue Management Guide https://www.cloudbeds.com/revenue-management/；SiteMinder 收益指标资料 https://www.siteminder.com/r/calculate-revpar/

业务原则：
- 收益管理不是单纯涨价，而是在需求、库存、渠道成本和客群结构之间找最优组合。
- 预测应关注未来需求，而不是只看昨天入住率；节假日、周末、周边活动、团队抵店都会改变需求曲线。
- 高入住压力下，优先保护高价值房型和直销渠道，谨慎释放低价渠道库存。
- 低入住压力下，先检查渠道曝光、价格竞争力、会员召回和套餐权益，而不是立即大幅降价。

值班经理动作：
- 若预测入住高于 85%：检查超售风险、保留应急房、确认客房清扫能力、前台晚高峰排班。
- 若预测营收下降但入住不低：复盘 ADR、团队价、OTA 佣金和折扣房占比。
- 若取消率预测上升：检查预付政策、活动变更、天气影响和高风险渠道。

可检索问题示例：明天入住率高该怎么调价？取消率上升要检查什么？营收下降但入住率不低怎么办？""",
        },
        {
            "title": "公开资料整理：前台班次开班、在岗、交接检查清单",
            "content": """分类：FRONT_DESK / 班次 SOP
来源：Canary Front Desk Checklist https://www.canarytechnologies.com/post/hotel-front-desk-checklist；Hotel Ops Guide Front Desk Shift Checklist https://hotelopsguide.com/blog/front-desk-shift-checklist/；LuxOps Front Office Checklist https://www.luxops.fr/en/hotel-front-office-checklist

开班检查：
- 登录 PMS、门锁、支付、发票和通讯系统，确认设备可用。
- 查看当日抵店、离店、续住、VIP、团队、特殊需求和欠费名单。
- 与客房部确认可售房、脏房、维修房、保留房和应急房。
- 核对备用金、房卡、发票纸、寄存牌、欢迎材料和交接未结事项。

在岗监控：
- 高峰前 2 小时确认预抵客人房态和房卡准备情况。
- 每 30-60 分钟与客房部同步一次高优先级清扫房。
- 对排队超过 5 分钟的客人主动说明等待时间，并安排分流办理。
- 所有投诉、换房、升级和补偿必须记录房号、原因、处理人和回访结果。

交接要求：
- 交接未完成投诉、待付款、待维修、晚到客、团队抵店、特殊发票和明日预抵压力。
- 夜审前复核当日房态、账务异常、No-show、取消和渠道订单。

可检索问题示例：前台晚班交接看什么？入住高峰如何分流？团队抵店前台怎么准备？""",
        },
        {
            "title": "公开资料整理：客诉处理与服务补救 SOP",
            "content": """分类：SERVICE_RECOVERY / 客诉闭环
来源：EHL Service Recovery Checklist https://hospitalityinsights.ehl.edu/hubfs/Blog-EHL-Insights/Download-resources/Service-Recovery-Checklist.pdf；Hotellier Guide 投诉处理 https://www.hotellierguide.com/hotel-guest-complaints-handling-how-hotels-can-resolve-issues-without-losing-guests/；Hospitality Institute Service Recovery https://hospitality.institute/bha105/mastering-service-recovery-guest-relations-hotels/

处理原则：
- 先听完，再复述问题，避免直接解释或推责。
- 道歉要针对具体问题，例如噪音、异味、等待、账单错误，而不是泛泛说“不好意思”。
- 处理方案要明确时间、责任人和回访节点。
- 补偿不是第一反应，先解决问题本身；必要时再由授权人员决定换房、减免、餐券或积分。

标准流程：
- 1 分钟内确认情绪：表达理解和歉意。
- 3 分钟内记录信息：房号、客人诉求、发生时间、涉及部门、证据。
- 10 分钟内给出初步方案：维修、换房、清洁、账务复核或经理介入。
- 30 分钟内回访：确认问题是否解决，未解决则升级。
- 当班闭环：记录原因分类、补救成本、责任岗位和预防动作。

高频场景：
- 噪音：先核实来源，提醒或协调；无法快速消除时优先换房。
- 异味/卫生：立即派客房主管复核，必要时深度清洁或换房。
- 排队等待：说明预计等待时间，分流预登记客人，给出明确办理顺序。
- 账单争议：先暂停争执，复核 PMS、支付流水和渠道订单，再由主管说明。

可检索问题示例：客人投诉房间异味怎么办？差评怎么闭环？什么时候给补偿？""",
        },
        {
            "title": "公开资料整理：客房、前台、维修协同与房态保障",
            "content": """分类：HOUSEKEEPING / 跨部门协同
来源：LuxOps Front Office Checklist https://www.luxops.fr/en/hotel-front-office-checklist；TargPatrol Hotel Front Desk Checklist https://targpatrol.com/checklists/hotel-front-desk-checklist/；Hotel Ops Guide 前台检查清单 https://hotelopsguide.com/blog/front-desk-shift-checklist/

协同目标：
- 前台关心可卖、可住、可解释，客房关心清洁、复检、异常，维修关心设备可用、风险隔离。三方必须使用统一房态。

房态优先级：
- 第一优先：已到店等待入住、VIP、团队领队房、亲子或老人特殊需求。
- 第二优先：预计 2 小时内抵店的预订已确认客人。
- 第三优先：延迟抵店、低风险散客、可沟通调整房型客人。
- 维修房、异味房、深度清洁房不得在未复检前释放。

高峰协同：
- 前台每小时给客房部一份预抵压力清单。
- 客房主管返回预计可交房时间，前台据此向客人说明等待预期。
- 若预测入住压力高，应预留 2-3 间机动房处理投诉、换房和超售风险。
- 若同一房型连续出现投诉，应触发维修或深洁复查，不继续出售。

可检索问题示例：入住高峰房态怎么协调？维修房什么时候能卖？客房清扫优先级怎么排？""",
        },
    ]

    created = []
    for doc in docs:
        if doc["title"] in existing_titles:
            continue
        result = request_json("/kb/docs", "POST", doc, token)
        created.append({"id": result["data"]["id"], "title": result["data"]["title"]})
    print(json.dumps({"created": created}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
