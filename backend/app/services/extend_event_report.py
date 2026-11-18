"""Extend an event report using trusted deployment shell access."""
import argparse
from datetime import datetime, timezone
from uuid import UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_id', type=UUID)
    parser.add_argument('expires_at', type=datetime.fromisoformat)
    parser.add_argument('--step-id', type=UUID,
                        help='Quiz step within this event; omit for a legacy single-session report')
    args = parser.parse_args()
    if args.expires_at.utcoffset() is None:
        parser.error('expires_at must include a timezone')
    from app.main import EventReport, EventStepReport, EventStepSession, SessionLocal
    from app.services.event_store import report_utc

    with SessionLocal() as db:
        if args.step_id is None:
            report = db.query(EventReport).filter_by(event_id=args.event_id.hex).with_for_update().first()
        else:
            link = db.query(EventStepSession).filter_by(
                event_id=args.event_id.hex, step_id=str(args.step_id)
            ).first()
            report = (db.query(EventStepReport).filter_by(instance_id=link.instance_id)
                      .with_for_update().first()) if link else None
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
