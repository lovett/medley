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

        let headers: {[name: string]: string} = {};

        if (req.method === 'GET') {
            headers['Accept'] = req.context.get(CONTENT_TYPE);
        } else {
            headers['Content-Type'] = req.context.get(CONTENT_TYPE);
        }

        let jsonRequest: HttpRequest<any> = req.clone({
            setHeaders: headers,
        });

        return next.handle(jsonRequest);
    }
}
