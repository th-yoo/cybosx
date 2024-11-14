import threading
import win32event

class InheritableEnumMeta(type):
    def __setattr__(cls, name, value):
        if name in cls.__dict__:
            raise AttributeError(f"Cannot reassign enum member '{name}'")
        super().__setattr__(name, value)

class InheritableEnum(metaclass=InheritableEnumMeta):
    @classmethod
    def members(cls):
        return {name: getattr(cls, name) for name in cls.__dict__ if not name.startswith('__')}


class Win32Thread(threading.Thread):
    class COM(InheritableEnum):
        stop  = -2
        start = -1
        
    def __init__(self):
        super().__init__()
        self._lock = threading.RLock()
        self._com_ev = win32event.CreateEvent(None, 0, 0, None)
        self._com = self.COM.stop
        self._args = []
        self._kwargs = {}
        self._rv_ev = win32event.CreateEvent(None, 0, 0, None)
        self._rv = None

        self._com_handler = None

    def run(self):
        #print('thread waiting for start signal')
        rv = win32event.WaitForSingleObject(self._com_ev, win32event.INFINITE)
        #print(f'WaitForSingleObject rv: {rv:08X}')
        try:
            if rv or self._com != self.COM.start:
                self._rv = RuntimeError(f'thread start failed')
                return
            else:
                self._rv = None
        finally:
            win32event.SetEvent(self._rv_ev)

        #print('thread started')

        waitables = [self._com_ev]
        while True:
            rc = win32event.MsgWaitForMultipleObjects(
                waitables,
                0,    # wait for any object
                win32event.INFINITE,
                win32event.QS_ALLEVENTS
            )
            if rc == win32event.WAIT_OBJECT_0:
                if self._invoke_command():
                    return
                continue

            if rc == win32event.WAIT_OBJECT_0 + len(waitables):
                wm_quit = python.PumpWaitingMessages()
                continue

            if rc == win32event.WAIT_TIMEOUT:
                print('Can not reach here!!!')
                break

            raise RuntimeError('Unexpected win32 wait return value')

    def _invoke_command(self):
        #print('handle command')
        try:
            if self._com == self.COM.stop:
                self._rv = None
                return True
            #print('com', self._com)
            #print('com_handler', self._com_handler[self._com])
            self._rv = self._com_handler[self._com](*self._args, **self._kwargs)
        except Exception as e:
            self._rv = e
        finally:
            win32event.SetEvent(self._rv_ev)
        return False
        
    def _invoke(self, command, *args, **kwargs):
        #print(f'_invoke {command}')
        with self._lock:
            #print('_invoke ...')
            self._com = command
            self._args = args
            self._kwargs = kwargs
            win32event.SetEvent(self._com_ev)
            win32event.WaitForSingleObject(self._rv_ev, win32event.INFINITE)
            return self._rv

    def start(self):
        with self._lock:
            #print('start')
            if not self.is_alive():
                #print('thread is not running')
                super().start()
                #print('invoke start')
                self._invoke(self.COM.start)
            
    def stop(self):
        with self._lock:
            if self.is_alive():
                self._invoke(self.COM.stop)

if __name__ == '__main__':
    t = Win32Thread()
    t.start()
    t.stop()
    t.join()
