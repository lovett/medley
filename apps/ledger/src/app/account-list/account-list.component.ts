import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';
import { AccountList } from '../types/AccountList';

@Component({
  selector: 'app-account-list',
  templateUrl: './account-list.component.html',
  styleUrls: ['./account-list.component.css']
})
export class AccountListComponent implements OnInit {
    count = 0;
    accounts: Account[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe({
            next: (accountList: AccountList) => {
                this.count = accountList.count;
                this.accounts = accountList.accounts.map((jsonAccount) => {
                    return Account.fromJson(jsonAccount);
                });
            },
            error: (err: Error) => console.log(err),
        });
    }

    activeAccounts(): Account[] {
        return this.accounts.filter(account => !account.closed_on);
    }

    inactiveAccounts(): Iterable<Account> {
        return this.accounts.filter(account => account.closed_on);
    }
}
