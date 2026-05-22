from ast import Index
from copy import deepcopy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler

def flag_translation(c):
    f = ''
    raw_flags = c
    for flag in raw_flags:
        if flag.isdigit():
            f += str(int(flag) - 1)
        else:
            f += flag
    if f != '*' and '-' not in f:
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

scheduler = BackgroundScheduler()
Base = declarative_base()

class Alarm(Base):
    __tablename__ = 'alarms'
    id = Column(Integer, primary_key = True, autoincrement = True)
    hour = Column(Integer, nullable = False)
    minute = Column(Integer, default=0)
    flags = Column(String, nullable = True)
    def __repr__(self):
        return f"ALARM id: {self.id} time_marker: {self.hour}:{self.minute} flags: {self.flags}"


engine = create_engine('sqlite:///database.sqlite', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def handle_alarm():
    print("alarm triggered")


scheduler.start()
with Session() as session:
    saved_alarms = session.query(Alarm).all()
    for alarm in saved_alarms:
        h, m = alarm.hour, alarm.minute
        flags = flag_translation(alarm.flags)
        scheduler.add_job(handle_alarm, trigger='cron', hour=int(h), minute=int(m), day_of_week = flags, id = str(alarm.id))
scheduler.print_jobs()

def display():
    global scheduler
    for job in scheduler.get_jobs():
        print(f'ID: {job.id}', end='\t')
        print(job.next_run_time.strftime('%H:%M'), end='\t')
        days = str(job.trigger.fields[4])
        for d in days:
            if d.isdigit():
                print(int(d) + 1, end='')
            else:
                print(d, end='')
        print()


while True:
    print('s - to set \nr - to remove\nd - to display')
    option = input()
    if option == 'd':
        display()
        input()
    if option == 's':
        while True:
            try:
                command = raw_command_translation(input())
                if not command: break
                with Session() as session:
                    new_alarm = Alarm(hour=command['hour'], minute = command['minute'], flags = command['raw_flags'])
                    session.add(new_alarm)
                    session.commit()
                    scheduler.add_job(handle_alarm, trigger='cron', hour=command['hour'], minute=command['minute'], day_of_week=command['flags'], id=str(new_alarm.id))
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