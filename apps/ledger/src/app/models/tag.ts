import { JsonTag } from '../types/JsonTag';

export class Tag {
    name: string = '';
    transaction_count: number = 0;
    last_used?: Date;

    constructor() {
    }

    static clone(tag: Tag): Tag {
        const t = new Tag();
        t.name = tag.name;
        t.transaction_count = tag.transaction_count;
        if (tag.last_used) {
            t.last_used = tag.last_used;
        }
        return t;
    }

    static fromString(name: string): Tag {
        const t = new Tag();
        t.name = name;
        return t;
    }

    static fromJson(json: JsonTag): Tag {
        const t = new Tag();
        t.name = json.name;
        t.transaction_count = json.transaction_count;
        if (json.last_used) {
            t.last_used = new Date(json.last_used);
        }
        return t;
    }

    asFormData(): FormData {
        const formData = new FormData();
        formData.set('name', this.name);
        return formData;
    }

    toString(): string {
        return this.name;
    }
}
