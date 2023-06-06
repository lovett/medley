import { AccountPrimitive } from '../types/accountPrimitive';

export class Account {
    uid: number;
    name: string;
    opened_on: Date;
    closed_on?: Date;
    url?: string;
    note?: string;

    constructor(primitive: AccountPrimitive) {
        this.uid = primitive.uid;
        this.name = primitive.name;
        this.opened_on = new Date(primitive.opened_on);
        if (primitive.closed_on) {
            this.closed_on = new Date(primitive.closed_on);
        }

        if (this.url) {
            this.url = primitive.url;
        }

        if (this.note) {
            this.note = primitive.note;
        }
    }

    openedOnYMD(): string {
        return this.dateValue(this.opened_on);
    }

    closedOnYMD(): string {
        return this.dateValue(this.closed_on);
    }

    dateValue(d?: Date): string {
        if (!d) {
            return '';
        }

        return d.toISOString().split('T')[0];
    }

    toPrimitive(): AccountPrimitive {
        return {
            uid: this.uid,
            name: this.name,
            opened_on: this.opened_on.toISOString().split('T')[0],
            closed_on: (this.closed_on)? this.closed_on.toISOString().split('T')[0] : undefined,
            note: this.note,
        }
    }
}
