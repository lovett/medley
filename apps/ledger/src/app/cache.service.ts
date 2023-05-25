import { Injectable } from '@angular/core';
import { HttpResponse } from '@angular/common/http';

@Injectable({
    providedIn: 'root'
})
export class CacheService {
    private requests: Map<string, HttpResponse<any>>;

    constructor() {
        this.requests = new Map();
    }

    put(url: string, response: HttpResponse<any>): void {
        this.requests.set(url, response);
    }

    get(url: string): HttpResponse<any> | undefined {
        return this.requests.get(url);
    }

    clear(url: string): void {
        this.requests.delete(url);
    }
}
