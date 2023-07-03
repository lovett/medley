import { TagPrimitive } from '../types/tagPrimitive';

export class Tag {
    name: string;
    transaction_count: number;
    last_used?: Date;

    constructor(primitive: TagPrimitive) {
        this.name = primitive.name;
        this.transaction_count = primitive.transaction_count;
        if (primitive.last_used) {
            this.last_used = new Date(primitive.last_used);
        }
    }
}
