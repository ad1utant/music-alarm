import time
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

def flag_translation(c):
    if c == '*' or c == 'a':
        return '*'
    f = ''
    raw_flags = c
    for flag in raw_flags:
        if flag.isdigit():
            f += str(int(flag) - 1)
        else:
            f += flag
    if '-' not in f:
        f = ",".join(f)
    return f

def raw_command_translation(com):
    if com == '':
        return False
    command = com.split()
    f = ''
    if len(command[0]) >= 3:
        h, m = int(command[0][:2]), int(command[0][2:])
    else:
        h, m = int(command[0]), 0
    if len(command) > 1:
        f = flag_translation(command[1])
        return {'hour' : h, 'minute' : m, 'flags' : f, 'raw_flags' : command[1]}
    else: return {'hour' : h, 'minute' : m, 'flags' : False, 'raw_flags' : False}

scheduler = BackgroundScheduler()
Base = declarative_base()

class Alarm(Base):
    __tablename__ = 'alarms'
    id = Column(Integer, primary_key = True, autoincrement = True)
    command = Column(String, nullable=False)
    def __repr__(self):
        return f"ALARM id: {self.id} command: {self.command}"


engine = create_engine('sqlite:///database.sqlite', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def handle_alarm(id, is_once):
    if is_once:
        with Session() as session:
            session.delete(session.query(Alarm).filter(Alarm.id == int(id)).first())
            session.commit()
    time.sleep(3)

def set_scheduler(command, id):
    if command['flags']:
        scheduler.add_job(handle_alarm, args=[id, False], trigger='cron', hour=command['hour'], minute=command['minute'], day_of_week=command['flags'], id=str(id))
    else:
        now = datetime.now()
        alarm_data = now.replace(hour=command['hour'], minute=command['minute'], second=0, microsecond=0)
        if alarm_data <= now:
            alarm_data += timedelta(days=1)
        scheduler.add_job(handle_alarm, args=[id, True], trigger='date', run_date=alarm_data, id=str(id))


scheduler.start()
with Session() as session:
    saved_alarms = session.query(Alarm).all()
    for alarm in saved_alarms:
        set_scheduler(raw_command_translation(alarm.command), alarm.id)
scheduler.print_jobs()

def display():
    global scheduler
    for job in scheduler.get_jobs():
        print(f'ID: {job.id}', end='\t')
        print(job.next_run_time.strftime('%H:%M'), end='\t')
        if isinstance(job.trigger, CronTrigger):
            days = str(job.trigger.fields[4])
            for d in days:
                if d.isdigit():
                    print(int(d) + 1, end='')
                else:
                    print(d, end='')
            print()
        if isinstance(job.trigger, DateTrigger):
            print(job.trigger.run_date.strftime('%d.%m.%Y'))



while True:
    print('s - to set \nr - to remove\nd - to display')
    option = input()
    if option == 'd':
        display()
        input()
    if option == 's':
        while True:
            try:
                raw_command = input()
                command = raw_command_translation(raw_command)
                if not command: break
                with Session() as session:
                    new_alarm = Alarm(command=raw_command)
                    session.add(new_alarm)
                    session.commit()
                    set_scheduler(command, new_alarm.id)
            except Exception:
                print('command you entered is incorrect')
    if option == 'r':
        display()
        while True:
            choice = input()
            if choice == '': break
            try:
                scheduler.remove_job(choice)
                with Session() as session:
                    alarm_to_delete = session.query(Alarm).filter(Alarm.id == int(choice)).first()
                    if alarm_to_delete:
                        session.delete(alarm_to_delete)
                        session.commit()
                print('alarm removed successfully')
            except Exception:
                print('id you entered is incorrect')
