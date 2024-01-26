import { Injectable } from '@angular/core';
import { HttpResponse } from '@angular/common/http';

@Injectable({
    providedIn: 'root'
})
export class CacheService {
    private requests: Map<string, HttpResponse<unknown>>;

    constructor() {
        this.requests = new Map();
    }

    put(url: string, response: HttpResponse<unknown>): void {
        this.requests.set(url, response);
    }

    get(url: string): HttpResponse<unknown> | undefined {
        return this.requests.get(url);
    }

    clear(url: string): void {
        this.requests.delete(url);
    }
}
