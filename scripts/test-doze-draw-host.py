#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise the production AOD draw controller with host Android fakes.

These lifecycle checks do not validate graphics/JNI, Dagger, Android resources or device behavior.
No Soong/lunch, ROM build, device command or external dependency installation is used.
"""
from pathlib import Path
import argparse
import subprocess
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
files={
'javax/inject/Inject.java':'package javax.inject; public @interface Inject {}',
'com/android/systemui/dagger/SysUISingleton.java':'package com.android.systemui.dagger; public @interface SysUISingleton {}',
'com/android/systemui/dagger/qualifiers/Main.java':'package com.android.systemui.dagger.qualifiers; public @interface Main {}',
'com/android/systemui/dagger/qualifiers/Background.java':'package com.android.systemui.dagger.qualifiers; public @interface Background {}',
'com/android/systemui/res/R.java':'package com.android.systemui.res; public class R { public static class bool { public static int doze_present_before_suspend=1; }}',
'com/android/window/flags/Flags.java':'package com.android.window.flags; public class Flags { public static boolean enabled=true; public static boolean sdkDesiredPresentTime(){return enabled;} }',
'android/content/Context.java':'''package android.content; public class Context { public boolean enabled=true; public Resources getResources(){return new Resources();} public class Resources {public boolean getBoolean(int id){return enabled;}} }''',
'android/util/Log.java':'package android.util; public class Log {public static int w(String t,String m){return 0;}public static int w(String t,String m,Throwable e){return 0;}}',
'android/os/Handler.java':'''package android.os; import java.util.*; public class Handler {public List<Runnable> immediate=new ArrayList<>(), delayed=new ArrayList<>(); public boolean post(Runnable r){immediate.add(r);return true;} public boolean postDelayed(Runnable r,long d){delayed.add(r);return true;}public void removeCallbacks(Runnable r){immediate.remove(r);delayed.remove(r);}public void flush(){while(!immediate.isEmpty())immediate.remove(0).run();}public void expire(){var a=new ArrayList<>(delayed);delayed.clear();a.forEach(Runnable::run);}}''',
'android/os/PowerManager.java':'''package android.os; public class PowerManager { public static final int DRAW_WAKE_LOCK=128;public int created;public WakeLock lock=new WakeLock();public WakeLock newWakeLock(int level,String tag){if(level!=128)throw new AssertionError();created++;return lock;}public static class WakeLock {public boolean held;public int acquired,released;public void setReferenceCounted(boolean b){if(b)throw new AssertionError();}public void acquire(){if(held)throw new AssertionError("double acquire");held=true;acquired++;}public void release(){if(!held)throw new AssertionError("double release");held=false;released++;}} }''',
'android/view/Display.java':'''package android.view; public class Display {public static final int STATE_UNKNOWN=0,STATE_OFF=1,STATE_ON=2,STATE_DOZE=3,STATE_DOZE_SUSPEND=4;public int state=4;public int getCommittedState(){return state;}public int getDisplayId(){return 0;} }''',
'android/hardware/display/DisplayManager.java':'''package android.hardware.display;import android.os.Handler; public class DisplayManager { public static final long EVENT_TYPE_DISPLAY_CHANGED=4,EVENT_TYPE_DISPLAY_REMOVED=2,PRIVATE_EVENT_TYPE_DISPLAY_COMMITTED_STATE_CHANGED=4;public int registered,removed;public long privateMask;public interface DisplayListener {void onDisplayAdded(int id);void onDisplayChanged(int id);void onDisplayRemoved(int id);}public void registerDisplayListener(DisplayListener l,Handler h,long mask,long priv){registered++;privateMask=priv;}public void unregisterDisplayListener(DisplayListener l){removed++;}}''',
'android/hardware/SyncFence.java':'''package android.hardware;import java.time.Duration; public class SyncFence implements AutoCloseable { public static final long SIGNAL_TIME_PENDING=Long.MAX_VALUE;public boolean valid=true,signaled=true,closed;public boolean isValid(){return valid;}public boolean await(Duration d){return signaled;}public long getSignalTime(){return signaled?1:SIGNAL_TIME_PENDING;}public void close(){closed=true;}}''',
'android/view/ViewTreeObserver.java':'''package android.view; public class ViewTreeObserver {public int added,removed;public interface OnPreDrawListener {boolean onPreDraw();}public void addOnPreDrawListener(OnPreDrawListener l){added++;}public void removeOnPreDrawListener(OnPreDrawListener l){removed++;}public boolean isAlive(){return true;}}''',
'android/view/View.java':'''package android.view;public class View { public boolean attached=true,hardware=true;public int invalidated;public Display display=new Display();public ViewTreeObserver observer=new ViewTreeObserver();public ViewRootImpl root=new ViewRootImpl();public interface OnAttachStateChangeListener{void onViewAttachedToWindow(View v);void onViewDetachedFromWindow(View v);}public void addOnAttachStateChangeListener(OnAttachStateChangeListener l){}public void removeOnAttachStateChangeListener(OnAttachStateChangeListener l){}public boolean isAttachedToWindow(){return attached;}public ViewTreeObserver getViewTreeObserver(){return observer;}public Display getDisplay(){return display;}public void invalidate(){invalidated++;}public ViewRootImpl getViewRootImpl(){return root;}public boolean isHardwareAccelerated(){return hardware;}}''',
'android/view/ViewRootImpl.java':'''package android.view;import java.util.*;public class ViewRootImpl {public List<SurfaceControl.Transaction> draws=new ArrayList<>();public boolean applyTransactionOnDraw(SurfaceControl.Transaction t){draws.add(t);return true;}}''',
'android/view/SurfaceControl.java':'''package android.view;import java.util.concurrent.Executor;import java.util.function.Consumer;import android.hardware.SyncFence;public class SurfaceControl {public static class TransactionStats {public SyncFence fence=new SyncFence();public SyncFence getPresentFence(){return fence;}public long getLatchTimeNanos(){return 1;}}public static class Transaction implements AutoCloseable {public Executor executor;public Consumer<TransactionStats> callback;public Transaction addTransactionCompletedListener(Executor e,Consumer<TransactionStats> c){executor=e;callback=c;return this;}public void complete(TransactionStats s){executor.execute(()->callback.accept(s));}public void close(){}}}''',
'com/android/systemui/doze/ControllerStateTest.java':'''package com.android.systemui.doze;
import android.content.*;import android.os.*;import android.view.*;import android.hardware.display.*;
public class ControllerStateTest {
 static int passed;static void check(boolean c){if(!c)throw new AssertionError();}
 static class F {Context c=new Context();PowerManager p=new PowerManager();Handler h=new Handler();DisplayManager d=new DisplayManager();View v=new View();DozeSuspendDrawController controller;
 F(){this(true);}F(boolean enabled){c.enabled=enabled;controller=new DozeSuspendDrawController(c,p,d,h,Runnable::run);controller.setView(v);}
 void begin(){controller.setScreenState(4);}void ready(){v.display.state=3;controller.onDisplayChanged(0);}SurfaceControl.Transaction frame(){check(controller.onPreDraw());return v.root.draws.get(v.root.draws.size()-1);}void complete(SurfaceControl.Transaction t){t.complete(new SurfaceControl.TransactionStats());h.flush();}
 }
 public static void main(String[] args){
  {F f=new F(false);f.begin();check(f.controller.onPreDraw());check(f.p.created==0&&f.d.registered==0);passed++;}
  {com.android.window.flags.Flags.enabled=false;F f=new F();f.begin();check(f.controller.onPreDraw());check(f.p.created==0&&f.d.registered==0);com.android.window.flags.Flags.enabled=true;passed++;}
  {F f=new F();f.begin();check(f.p.lock.held);check(!f.controller.onPreDraw());check(f.d.privateMask==DisplayManager.PRIVATE_EVENT_TYPE_DISPLAY_COMMITTED_STATE_CHANGED);f.ready();check(f.v.invalidated>0);var t=f.frame();check(f.p.lock.held);f.complete(t);check(!f.p.lock.held&&f.p.lock.released==1);passed++;}
  {F f=new F();f.begin();f.ready();var a=f.frame();var b=f.frame();f.complete(a);check(f.p.lock.held);f.complete(b);check(!f.p.lock.held);passed++;}
  {F f=new F();f.begin();f.ready();var old=f.frame();f.controller.setScreenState(2);check(!f.p.lock.held);f.begin();var next=f.frame();f.complete(old);check(f.p.lock.held);f.complete(next);check(!f.p.lock.held);passed++;}
  {F f=new F();f.begin();f.h.expire();check(!f.p.lock.held&&f.d.removed==1);check(f.controller.onPreDraw());check(f.p.lock.acquired==1);f.controller.setScreenState(2);f.begin();check(f.p.lock.acquired==2);passed++;}
  {F f=new F();f.begin();f.ready();var t=f.frame();var s=new SurfaceControl.TransactionStats();s.fence.valid=false;t.complete(s);f.h.flush();check(s.fence.closed&&!f.p.lock.held&&f.d.removed==1);check(f.controller.onPreDraw()&&f.p.lock.acquired==1);passed++;}
  {F f=new F();f.begin();f.ready();var t=f.frame();f.controller.onViewDetachedFromWindow(f.v);check(!f.p.lock.held&&f.d.removed==1);f.controller.onViewAttachedToWindow(f.v);check(f.p.lock.held);f.complete(t);check(f.p.lock.held);passed++;}
  {F f=new F();f.begin();f.ready();f.v.hardware=false;check(f.controller.onPreDraw());check(!f.p.lock.held&&f.d.removed==1);passed++;}
  {F f=new F();f.begin();f.ready();var t=f.frame();var s=new SurfaceControl.TransactionStats();s.fence.signaled=false;t.complete(s);f.h.flush();check(!f.p.lock.held&&s.fence.closed);f.controller.setScreenState(0);check(f.p.lock.released==1);passed++;}
  {F f=new F();f.begin();f.ready();f.complete(f.frame());f.v.display.state=4;check(!f.controller.onPreDraw());check(f.p.lock.acquired==2);f.ready();f.complete(f.frame());check(f.p.lock.released==2);passed++;}
  System.out.println("PASS "+passed+" lifecycle scenarios (host Android fakes; not device/graphics validation)");
 }
}'''
}
for name,contents in files.items():
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(contents+'\n')
src=SRC_ROOT/'frameworks/base/packages/SystemUI/src/com/android/systemui/doze/DozeSuspendDrawController.java'
jdk=SRC_ROOT/'prebuilts/jdk/jdk21/linux-x86/bin'
subprocess.run([str(jdk/'javac'),'-J-Xmx128m','-proc:none','-d',str(D/'classes')]+[str(D/x) for x in files]+[str(src)],check=True)
subprocess.run([str(jdk/'java'),'-Xmx128m','-cp',str(D/'classes'),'com.android.systemui.doze.ControllerStateTest'],check=True)
