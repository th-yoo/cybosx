import asyncio
import inspect
import threading
from typing import Callable, List, Set, TypeVar, Union, Optional
import logging

# Define a type variable for the resource type
T = TypeVar('T')

# Set up logging
logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.INFO)

DisposeFunc = Callable[[object], Union[None, asyncio.Future]]

class ResourcePool:
    def __init__(
        self,
        create: Callable[[int], Union[object, asyncio.Future]],
        max_resources: int = 0, # no limit
        dispose: Optional[DisposeFunc] = None
    ):
        if max_resources < 0:
            raise ValueError(f'max_resources cannot be negative: {max_resources}')
        self._max_resources: int = max_resources
        self._available_resources: List[object] = []
        self._used_resources: Set[object] = set()
        self._create: Callable[[int], Union[object, asyncio.Future]] = create
        self._dispose: Optional[DisposeFunc] = dispose
        self._shuttingdown = False
        self._shutdown_event: threading.Event = threading.Event()
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_resources) if max_resources > 0 else None

    def _create_resource(self, resource_id: int) -> object:
        if inspect.iscoroutinefunction(self._create):
            return asyncio.run(self._create(resource_id))
        return self._create(resource_id)

    async def get(self) -> object:
        return await asyncio.to_thread(self._get)
    async def put(self, resource):
        return await asyncio.to_thread(self._put, resource)

    def _get(self) -> object:
        if self._max_resources:
            self._semaphore.acquire()

        with self._lock:
            if self._shuttingdown:
                raise Exception("Pool is shutting down, cannot acquire new resources.")

            # If there are no available resources, and we can still create more
            if not self._available_resources and (not self._max_resources or len(self._used_resources) < self._max_resources):
                resource = self._create_resource(len(self._used_resources))  # Create a new resource
                logger.info(f"Created new resource {resource}")
            else:
                # Reuse an existing resource from the available pool
                resource = self._available_resources.pop()
                logger.info(f"Reusing resource {resource}")
            
            # Mark the resource as used
            self._used_resources.add(resource)

        return resource

    def _put(self, resource: object) -> None:
        with self._lock:
            if resource in self._used_resources:
                self._used_resources.remove(resource)
                self._available_resources.append(resource)  # Return the resource to the available pool
                if self._max_resources:
                    self._semaphore.release()  # Increment the semaphore count
                logger.info(f"Released resource {resource}")
                
                if not self._used_resources:
                    logger.info('All resources are returned')

                # Check if all resources are put back and shutdown is requested
                if (
                    not self._used_resources and
                    self._shuttingdown
                ):
                    logger.info("All resources are returned, triggering shutdown event.")
                    self._shutdown_event.set()
            else:
                logger.error(f"Error: Resource {resource} not in use.")

    async def shutdown(self, force=False):
        await asyncio.to_thread(self._shutdown, force)

    def _shutdown(self, force=False) -> None:
        logger.info("Shutting down the resource pool...")

        self._lock.acquire()
        if self._shuttingdown:
            logger.info("Pool is already shutting down.")
            self._lock.release()
            return
        self._shuttingdown = True

        resources = self._available_resources
        if force:
            resources += list(self._used_resources)  # Force dispose of both used and available resources
        elif self._used_resources:
            # Wait for the shutdown event to be triggered (all resources returned)
            logger.info("Waiting for all resources to be returned.")
            self._lock.release()
            self._shutdown_event.wait()
            self._lock.acquire()

        # Optionally, dispose of remaining resources if needed
        if self._dispose:
            for resource in resources:
                if inspect.iscoroutinefunction(self._dispose):
                    asyncio.run(self._dispose(resource))
                else:
                    self._dispose(resource)

        self._lock.release()
        logger.info("Resource pool shutdown complete.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        force = exc_value is not None
        self._shutdown(force)

if __name__ == '__main__':
    import time
    from .eventsink_thread import EventSinkThread
    from .util import singletonize
    async def main():
        #getinst = singletonize(AsyncResourcePool(lambda n: n, 3))
        getinst = singletonize(AsyncResourcePool(lambda n: n))
        r0 = await getinst().get()
        print('r0', r0)
        r1 = await getinst().get()
        print('r1', r1)
        r2 = await getinst().get()
        print('r2', r2)
        await getinst().put(r0)
        r3 = await getinst().get()
        print('r3', r3)
    #asyncio.run(main())

    async def test_shutdown():
        #getinst = singletonize(AsyncResourcePool(lambda n: n, 3))
        getinst = singletonize(AsyncResourcePool(lambda n: n))
        r0 = await getinst().get()
        print('r0', r0)
        r1 = await getinst().get()
        print('r1', r1)
        r2 = await getinst().get()
        print('r2', r2)
        task = asyncio.create_task(getinst().shutdown(False))
        await getinst().put(r0)
        await getinst().put(r1)
        await getinst().put(r2)
        #await task

    #asyncio.run(test_shutdown())
    def create_thread(id):
        thread = EventSinkThread(f'thread_{id:02d}')
        thread.start()
        return thread

    def dispose_thread(thread):
        thread.stop()
        thread.join()

    pool = ResourcePool(create_thread, 0, dispose_thread)

    def thread_proc():
        t = pool.get()
        time.sleep(1)
        pool.put(t)

    t1 = threading.Thread(target=thread_proc) 
    t2 = threading.Thread(target=thread_proc)
    t1.start(); t2.start()
    t1.join()
    t2.join()
    pool.shutdown(False)
