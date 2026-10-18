"""Read-only monthly committee view. Author: Abdelhalim Talbi."""
import calendar
from datetime import date

class MonthView:
    def __init__(self, committee_calendar):
        self.calendar = committee_calendar

    def build(self, year, month, owner='', meeting_status=''):
        if type(year) is not int or type(month) is not int or not 1 <= year <= 9999 or not 1 <= month <= 12:
            raise ValueError('Invalid year or month')
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        snapshot = self.calendar.snapshot(first.isoformat(), (last-first).days)
        meetings = [m for m in snapshot['meetings'] if not meeting_status or m['status'] == meeting_status]
        followups = [f for f in snapshot['followups'] if first.isoformat() <= f['due_date'] <= last.isoformat() and (not owner or f['owner'].casefold() == owner.casefold())]
        days = {}
        for m in meetings: days.setdefault(m['date'], []).append({'kind':'MEETING', **m})
        for f in followups: days.setdefault(f['due_date'], []).append({'kind':'FOLLOWUP', **f})
        return {'year':year, 'month':month, 'days':days, 'meetings':meetings, 'followups':followups,
                'weeks':calendar.Calendar(firstweekday=0).monthdatescalendar(year,month)}
