import { JsonAccount } from '../types/JsonAccount';

export class Account {
    uid: number = 0;
    name: string = '';
    opened_on: Date = new Date();
    closed_on?: Date;
    url?: string;
    note?: string;
    balance: number = 0;
    total_pending: number = 0;
    last_active?: Date;

    constructor() {
    }

    static clone(account: Account): Account {
        const a = new Account();
        a.uid = account.uid;
        a.name = account.name;
        a.opened_on = account.opened_on;
        a.closed_on = account.closed_on;
        a.url = account.url;
        a.note = account.note;
        a.balance = account.balance;
        a.total_pending = account.total_pending;
        a.last_active = account.last_active;
        return a;
    }

    static fromJson(json: JsonAccount): Account {
        const a = new Account();
        a.uid = json.uid;
        a.name = json.name;
        a.balance = json.balance;
        a.total_pending = json.total_pending;

        if (json.opened_on) {
            a.opened_on = new Date(json.opened_on);
        }

        if (json.closed_on) {
            a.closed_on = new Date(json.closed_on);
        }

        if (json.last_active) {
            a.last_active = new Date(json.last_active);
        }

        if (json.url) {
            a.url = json.url;
        }

        if (json.note) {
            a.note = json.note;
        }

        return a;
    }

    asFormData(): FormData {
        const formData = new FormData();
        formData.set('name', this.name);
        formData.set('opened_on', this.opened_on.toString());

        if (this.closed_on) {
            formData.set('closed_on', this.closed_on.toString());
        }

        if (this.url) {
            formData.set('url', this.url);
        }

        if (this.note) {
            formData.set('note', this.note);
        }

        return formData;

    }


    openedOnYMD(): string {
        return this.dateValue(this.opened_on);
    }

    closedOnYMD(): string {
        return this.dateValue(this.closed_on);
    }

    dateValue(d?: Date): string {
        if (d) {
            return d.toISOString().split('T')[0];
        }

        return '';
    }
}
