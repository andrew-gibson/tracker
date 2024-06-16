from datetime import datetime, timedelta

def get_last_n_weeks(n):
    today = datetime.today()
    weeks = []
    for i in range(n):
        week_start = today - timedelta(days=today.weekday() + 7 * i)
        week_end = week_start + timedelta(days=6)
        weeks.append({
            "week_start" : week_start,
            "name" :   " to ".join([week_start.strftime('%m-%d'), week_end.strftime('%m-%d')])
        })
    return weeks

