from datetime import datetime, timedelta


def get_last_n_weeks(n):
    today = datetime.today()
    weeks = []
    for i in range(n):
        week_start = today - timedelta(days=today.weekday() + 7 * i)
        week_end = week_start + timedelta(days=4)
        if week_start.month == week_end.month:
            weeks.append(
                {
                    "week_start": week_start.strftime("%Y-%m-%d"),
                    "name": "  —  ".join(
                        [week_start.strftime("%b %d"), week_end.strftime("%d")]
                    ),
                }
            )
        else:
            weeks.append(
                {
                    "week_start": week_start.strftime("%Y-%m-%d"),
                    "name": "  —  ".join(
                        [week_start.strftime("%b %d"), week_end.strftime("%b %d")]
                    ),
                }
            )

    return weeks
