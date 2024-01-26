import { Injectable } from '@angular/core';
import {
    HttpRequest,
    HttpHandler,
    HttpEvent,
    HttpInterceptor,
    HttpContextToken
} from '@angular/common/http';
import { Observable } from 'rxjs';

export const CONTENT_TYPE = new HttpContextToken(() => 'application/json');

@Injectable()
export class ContentTypeInterceptor implements HttpInterceptor {

    constructor() {}

    intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        console.log('JsonInterceptor', req.url);

        const headers: {[name: string]: string} = {};

        if (req.method === 'GET') {
            headers['Accept'] = req.context.get(CONTENT_TYPE);
        } else {
            headers['Content-Type'] = req.context.get(CONTENT_TYPE);
        }

        const jsonRequest: HttpRequest<unknown> = req.clone({
            setHeaders: headers,
        });

        return next.handle(jsonRequest);
    }
}
