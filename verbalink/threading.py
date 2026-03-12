"""Thread lifecycle helpers for Verbalink."""

from PyQt5.QtCore import QObject, QThread


class ThreadManager(QObject):
    """Manage worker/thread pairs and cleanly stop them when needed."""

    def __init__(self):
        super().__init__()
        self.threads = []

    def start_thread(self, worker_class, *args, **kwargs):
        thread = QThread()
        worker = worker_class(*args, **kwargs)
        self.threads.append((thread, worker))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.remove_thread(thread))
        thread.start()
        return worker

    def remove_thread(self, thread):
        self.threads = [(t, w) for t, w in self.threads if t != thread]

    def stop_all_threads(self):
        for thread, worker in self.threads:
            if hasattr(worker, "stop"):
                worker.stop()
            thread.quit()
            thread.wait()
