import { Injectable } from '@angular/core';
import {
    HttpRequest,
    HttpResponse,
    HttpHandler,
    HttpEvent,
    HttpInterceptor,
    HttpContextToken,
} from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';
import { CacheService } from '../cache.service';

export const NOCACHE = new HttpContextToken(() => false);

@Injectable()
export class CacheInterceptor implements HttpInterceptor {

    constructor( private cacheService: CacheService) {}

    intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        if (req.context.get(NOCACHE)) {
            return next.handle(req);
        }

        if (req.method !== 'GET') {
            // TODO: add invalidation
            return next.handle(req);
        }

        const cachedResponse = this.cacheService.get(req.url);

        if (cachedResponse) {
            console.log('Cache hit', req.url);
            return of(cachedResponse);
        }

        console.log('Cache miss', req.url);

        return next.handle(req)
            .pipe(
                tap(event => {
                    if (event instanceof HttpResponse) {
                        console.log(`Caching ${req.url}`);
                        this.cacheService.put(req.url, event);
                    }
                })
            );
    }
}
