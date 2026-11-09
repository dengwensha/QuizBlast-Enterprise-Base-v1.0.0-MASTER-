"""Extend an event report using trusted deployment shell access."""
import argparse
from datetime import datetime, timezone
from uuid import UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_id', type=UUID)
    parser.add_argument('expires_at', type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.expires_at.utcoffset() is None:
        parser.error('expires_at must include a timezone')
    from app.main import EventReport, SessionLocal
    from app.services.event_store import report_utc

    with SessionLocal() as db:
        report = db.query(EventReport).filter_by(event_id=args.event_id.hex).with_for_update().first()
        if report is None:
            parser.error('event report not found')
        if report_utc(report.expires_at) <= datetime.now(timezone.utc):
            parser.error('event report has expired')
        if args.expires_at <= report_utc(report.expires_at):
            parser.error('new expiry must be later than current expiry')
        report.expires_at = args.expires_at.astimezone(timezone.utc)
        db.commit()
    print(args.expires_at.isoformat())


if __name__ == '__main__':
    main()
