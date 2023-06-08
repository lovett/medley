import { AccountPrimitive } from '../types/accountPrimitive';

export class Account {
    uid: number;
    name: string;
    opened_on?: Date;
    closed_on?: Date;
    url?: string;
    note?: string;
    isCredit: boolean;

    constructor(primitive: AccountPrimitive) {
        this.uid = primitive.uid;
        this.name = primitive.name;

        if (primitive.opened_on) {
            this.opened_on = new Date(primitive.opened_on);
        }

        if (primitive.closed_on) {
            this.closed_on = new Date(primitive.closed_on);
        }

        if (primitive.url) {
            this.url = primitive.url;
        }

        if (primitive.note) {
            this.note = primitive.note;
        }

        this.isCredit = Boolean(primitive.is_credit)
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
