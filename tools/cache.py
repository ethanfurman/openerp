import lru

class ormcache(object):
    """ LRU cache decorator for orm methods,
    """

    def __init__(cache, skiparg=2, size=8192, multi=None, timeout=None):
        cache.skiparg = skiparg
        cache.size = size
        cache.method = None
        cache.stat_miss = 0
        cache.stat_hit = 0
        cache.stat_err = 0

    def __call__(cache, m):
        cache.method = m
        def lookup(model, cr, *args):
            r = cache.lookup(model, cr, *args)
            return r
        lookup.clear_cache = cache.clear
        return lookup

    def stat(cache):
        return "lookup-stats hit=%s miss=%s err=%s ratio=%.1f" % (
                cache.stat_hit, cache.stat_miss, cache.stat_err, (100*float(cache.stat_hit))/(cache.stat_miss+cache.stat_hit)
                )

    def lru(cache, model):
        try:
            ormcache = getattr(model, '_ormcache')
        except AttributeError:
            ormcache = model._ormcache = {}
        try:
            d = ormcache[cache.method]
        except KeyError:
            d = ormcache[cache.method] = lru.LRU(cache.size)
        return d

    def lookup(cache, model, cr, *args):
        d = cache.lru(model)
        key = args[cache.skiparg-2:]
        try:
           r = d[key]
           cache.stat_hit += 1
           return r
        except KeyError:
           cache.stat_miss += 1
           value = d[key] = cache.method(model, cr, *args)
           return value
        except TypeError:
           cache.stat_err += 1
           return cache.method(model, cr, *args)

    def clear(cache, model, *args):
        """ Remove *args entry from the cache or all keys if *args is undefined
        """
        d = cache.lru(model)
        if args:
            try:
                key = args[cache.skiparg-2:]
                del d[key]
                model.pool._any_cache_cleared = True
            except KeyError:
                pass
        else:
            d.clear()
            model.pool._any_cache_cleared = True

class ormcache_multi(ormcache):
    def __init__(cache, skiparg=2, size=8192, multi=3):
        super(ormcache_multi, cache).__init__(skiparg, size)
        cache.multi = multi - 2

    def lookup(cache, model, cr, *args):
        d = cache.lru(model)
        args = list(args)
        multi = cache.multi
        ids = args[multi]
        r = {}
        miss = []

        for i in ids:
            args[multi] = i
            key = tuple(args[cache.skiparg-2:])
            try:
               r[i] = d[key]
               cache.stat_hit += 1
            except Exception:
               cache.stat_miss += 1
               miss.append(i)

        if miss:
            args[multi] = miss
            r.update(cache.method(model, cr, *args))

        for i in miss:
            args[multi] = i
            key = tuple(args[cache.skiparg-2:])
            d[key] = r[i]

        return r

class dummy_cache(object):
    """ Cache decorator replacement to actually do no caching.
    """
    def __init__(self, *l, **kw):
        pass
    def __call__(self, fn):
        fn.clear_cache = self.clear
        return fn
    def clear(self, *l, **kw):
        pass

if __name__ == '__main__':

    class NS(object):
        pass

    class A(object):
        def __init__(self):
            self.pool = NS()
        @ormcache()
        def m(self, a, b):
            print  "A::m(", self, a, b, ")"
            return 1

        @ormcache_multi(multi=3)
        def n(self, cr, uid, ids):
            print  "m", self, cr, uid, ids
            return dict([(i, i) for i in ids])

    a=A()
    r = a.m(1, 2)
    r = a.m(1, 2)
    print
    r = a.n("cr", 1, [1 ,2 ,3 ,4])
    r = a.n("cr", 1, [1, 2])
    print
    for i in a._ormcache:
        print a._ormcache[i].d
    a.n.clear_cache(a, 1, 1)
    r = a.n("cr", 1, [1, 2])
    print r
    r = a.n("cr", 1, [1 ,2])

# For backward compatibility
cache = ormcache

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
