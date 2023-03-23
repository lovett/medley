import { Attribute, Component, Input, OnInit, EventEmitter } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';

@Component({
  selector: 'app-account-menu',
  templateUrl: './account-menu.component.html',
  styleUrls: ['./account-menu.component.css'],
})
export class AccountMenuComponent implements OnInit {
    @Input() form!: FormGroup;
    @Input() account?: Account;
    accounts: Account[] = [];

    constructor(
        private ledgerService: LedgerService
    ) {}

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe(
            (accounts: Account[]) => this.accounts = accounts,
            (err: any) => console.log(err),
            () => console.log('All done getting accounts for menu')
        );
    }
}