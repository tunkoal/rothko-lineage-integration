#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise the production special-trigger adapter with small host Android fakes."""
from pathlib import Path
import subprocess
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
SRC_ROOT = args.source_root.resolve()
D = args.output.resolve()
if D.exists() or D.is_relative_to(SRC_ROOT):
    parser.error('output must be new and outside the source tree')
if not (SRC_ROOT / 'prebuilts/jdk/jdk21/linux-x86/bin/javac').is_file():
    parser.error('source tree JDK21 linux-x86 javac is required')
D.mkdir(parents=True, exist_ok=False)
SRC = SRC_ROOT
JDK = SRC / 'prebuilts/jdk/jdk21/linux-x86/bin'

files = {
    'android/hardware/Sensor.java': '''package android.hardware;
public class Sensor {
 public static final int REPORTING_MODE_SPECIAL_TRIGGER=3;
 public int mode=3; public boolean wake=true;
 public int getReportingMode(){return mode;}
 public boolean isWakeUpSensor(){return wake;}
}''',
    'android/hardware/SensorEvent.java': '''package android.hardware;
public class SensorEvent {
 public Sensor sensor; public float[] values;
 public SensorEvent(Sensor s,float...v){sensor=s;values=v;}
}''',
    'android/hardware/SensorEventListener.java': '''package android.hardware;
public interface SensorEventListener {
 void onAccuracyChanged(Sensor s,int a);void onSensorChanged(SensorEvent e);
}''',
    'android/hardware/SensorManager.java': '''package android.hardware;
import android.os.Handler;
public class SensorManager {
 public static final int SENSOR_DELAY_NORMAL=3;
 public int registers,unregisters;public boolean success=true;
 public SensorEventListener listener;
 public boolean registerListener(SensorEventListener l,Sensor s,int delay,Handler h){
  registers++;listener=l;return success;
 }
 public void unregisterListener(SensorEventListener l,Sensor s){
  if(l==null)throw new AssertionError("null listener");unregisters++;
 }
}''',
    'android/os/Handler.java': '''package android.os;
import java.util.ArrayDeque;
public class Handler {
 public final ArrayDeque<Runnable> queue=new ArrayDeque<>();
 public boolean post(Runnable r){queue.add(r);return true;}
 public void drain(){while(!queue.isEmpty())queue.remove().run();}
}''',
    'com/android/systemui/util/wakelock/WakeLock.java': '''package com.android.systemui.util.wakelock;
public interface WakeLock { Runnable wrap(Runnable r); }''',
    'com/android/systemui/doze/PickupListenerTest.java': '''package com.android.systemui.doze;
import android.hardware.*;
import android.os.Handler;
import com.android.systemui.util.wakelock.WakeLock;
import java.util.*;
public class PickupListenerTest {
 static void check(boolean b){if(!b)throw new AssertionError();}
 static class Lock implements WakeLock {
  int held;
  public Runnable wrap(Runnable r){held++;return ()->{try{r.run();}finally{held--;}};}
 }
 static class Fixture {
  final Sensor sensor=new Sensor();final SensorManager manager=new SensorManager();
  final Handler handler=new Handler();final Lock lock=new Lock();
  final List<Float> values=new ArrayList<>();
  final DozePickupListener pickup=new DozePickupListener(manager,sensor,handler,lock,
    v->values.add(v[0]));
  void emit(float...v){manager.listener.onSensorChanged(new SensorEvent(sensor,v));}
 }
 public static void main(String[] args){
  Fixture f=new Fixture();check(f.pickup.setListening(false)==false);
  check(f.manager.registers==0 && f.manager.unregisters==0);
  check(f.pickup.setListening(true));check(f.pickup.setListening(true));
  check(f.manager.registers==1);
  f.emit(0);f.emit(2);f.emit();f.emit(Float.NaN);f.handler.drain();
  check(f.values.isEmpty() && f.lock.held==0);
  System.out.println("PASS idle/idempotent/filter");

  float[] raw={1,7};SensorEvent e=new SensorEvent(f.sensor,raw);
  f.manager.listener.onSensorChanged(e);raw[0]=2;f.handler.drain();
  check(f.values.equals(List.of(1f)) && f.lock.held==0);
  System.out.println("PASS event-copy/pickup-delivery");

  f.emit(1);check(f.lock.held==1);f.pickup.setListening(false);f.handler.drain();
  check(f.values.size()==1 && f.lock.held==0 && f.manager.unregisters==1);
  f.pickup.setListening(false);check(f.manager.unregisters==1);
  System.out.println("PASS cancelled-queued-event/balanced-lock");

  SensorEventListener old=f.manager.listener;f.pickup.setListening(true);
  old.onSensorChanged(new SensorEvent(f.sensor,1));f.emit(1);f.handler.drain();
  check(f.values.size()==2 && f.lock.held==0);
  System.out.println("PASS stale-listener-after-reregistration");

  f.manager.listener.onSensorChanged(new SensorEvent(new Sensor(),1));f.handler.drain();
  check(f.values.size()==2);
  System.out.println("PASS unrelated-sensor-ignored");

  Fixture failed=new Fixture();failed.manager.success=false;
  check(!failed.pickup.setListening(true));failed.emit(1);failed.handler.drain();
  check(failed.values.isEmpty() && failed.lock.held==0);
  failed.manager.success=true;check(failed.pickup.setListening(true));
  check(failed.manager.registers==2);failed.emit(1);failed.handler.drain();
  check(failed.values.size()==1);
  System.out.println("PASS failed-registration/retry");

  for(int mode:new int[]{0,1,2}){
   Sensor bad=new Sensor();bad.mode=mode;
   try{new DozePickupListener(f.manager,bad,f.handler,f.lock,v->{});
    throw new AssertionError("invalid mode accepted");}catch(IllegalArgumentException ok){}
  }
  Sensor nonWake=new Sensor();nonWake.wake=false;
  try{new DozePickupListener(f.manager,nonWake,f.handler,f.lock,v->{});
   throw new AssertionError("nonwake accepted");}catch(IllegalArgumentException ok){}
  System.out.println("PASS unsupported-mode/non-wakeup-rejected");

  Fixture reentrant=new Fixture();DozePickupListener[] adapter=new DozePickupListener[1];
  adapter[0]=new DozePickupListener(reentrant.manager,reentrant.sensor,
    reentrant.handler,reentrant.lock,v->adapter[0].setListening(false));
  check(adapter[0].setListening(true));reentrant.emit(1);reentrant.handler.drain();
  check(reentrant.manager.unregisters==1 && reentrant.lock.held==0);
  System.out.println("PASS callback-reentrant-disable");
 }
}''',
}

for name, content in files.items():
    p = D / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content + '\n')
production = SRC / 'frameworks/base/packages/SystemUI/src/com/android/systemui/doze/DozePickupListener.java'
subprocess.run([str(JDK / 'javac'), '-J-Xmx128m', '-proc:none', '-d', str(D / 'classes')]
               + [str(D / x) for x in files] + [str(production)], check=True)
subprocess.run([str(JDK / 'java'), '-Xmx128m', '-cp', str(D / 'classes'),
                'com.android.systemui.doze.PickupListenerTest'], check=True)
